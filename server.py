
import os
import shutil
import uvicorn
import logging
import configparser
import subprocess
import json
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from fastapi.encoders import jsonable_encoder
import numpy as np
import sqlite3
import pandas as pd

# Import the existing auditor class and the logger
from trade_check import TradeAuditor, logger, UPGRADE_CRITERIA, list_trade_files
from import_kdata import run_kdata_import

app = FastAPI()

# --- Dynamic Path Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "trade_notes.db")
KDATA_DIRECTORY = os.path.join(SCRIPT_DIR, "KData")
TRADEDATA_DIRECTORY = os.path.join(SCRIPT_DIR, "tradedata")
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.ini')

def init_database():
    """Initializes the database and creates tables if they don't exist."""
    try:
        logger.info(f"Initializing database at {DB_FILE}...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Create table for trade notes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_notes (
                trade_id TEXT PRIMARY KEY,
                note TEXT,
                related_info TEXT,
                last_updated TIMESTAMP
            )
        ''')

        # Create table for trades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                trade_time DATETIME,
                action TEXT,
                net_pnl REAL,
                contracts INTEGER,
                product_name TEXT,
                source_file TEXT
            )
        ''')

        # Create table for market data (K-line)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                datetime TEXT PRIMARY KEY,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully with all tables.")
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}", exc_info=True)
        # We might want to prevent the app from starting if the DB fails
        raise

@app.on_event("startup")
async def startup_event():
    """Run database initialization on server startup."""
    init_database()

# --- Database Setup ---

@app.get("/api/kdata-files")
async def get_kdata_files():
    """API endpoint to list all available .csv files in the 'KData' directory."""
    logger.info("Request received for KData files list.")
    try:
        if not os.path.isdir(KDATA_DIRECTORY):
            logger.warning(f"'{KDATA_DIRECTORY}' directory not found.")
            return JSONResponse(content={"files": []})
            
        files = [f for f in os.listdir(KDATA_DIRECTORY) if f.endswith('.csv') and os.path.isfile(os.path.join(KDATA_DIRECTORY, f))]
        return JSONResponse(content={"files": sorted(files)})
    except Exception as e:
        logger.error(f"Failed to list KData files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve KData files from server.")

@app.get("/api/kline_data")
async def get_kline_data(timeframe: Optional[str] = '1T'): # Default to 1-minute
    """
    API endpoint to retrieve K-line data from the database, formatted for charting.
    Supports resampling to different timeframes.
    """
    logger.info(f"Request received for K-line data with timeframe: {timeframe}")
    try:
        conn = sqlite3.connect(DB_FILE)
        query = "SELECT datetime, open, high, low, close, volume FROM market_data ORDER BY datetime ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        logger.info(f"K-line trace: Read {len(df)} rows from database.")

        if df.empty:
            logger.warning("No K-line data found in 'market_data' table.")
            return JSONResponse(content=[])

        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')

        if timeframe and timeframe != '1T':
            try:
                df_resampled = df.resample(timeframe).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                })
                logger.info(f"K-line trace: Resampled to {len(df_resampled)} rows before dropping NA.")

                df_resampled.dropna(subset=['open', 'high', 'low', 'close'], how='all', inplace=True)
                logger.info(f"K-line trace: {len(df_resampled)} rows remain after dropping rows with no OHLC.")

                if df_resampled.empty:
                    logger.warning(f"No K-line data found after resampling to {timeframe}.")
                    return JSONResponse(content=[])

                df = df_resampled
            except Exception as e:
                logger.error(f"Error during resampling with timeframe '{timeframe}': {e}", exc_info=True)
                raise HTTPException(status_code=400, detail=f"Invalid timeframe or resampling error: {timeframe}")

        df = df.reset_index()

        df.replace({np.nan: None}, inplace=True)
        
        df['time'] = df['datetime'].astype('int64') // 10**9
        df.rename(columns={'volume': 'value'}, inplace=True)
        
        chart_data = df[['time', 'open', 'high', 'low', 'close', 'value']].to_dict(orient='records')
        
        logger.info(f"K-line trace: Final chart_data has {len(chart_data)} records.")
        return JSONResponse(content=chart_data)
        
    except sqlite3.OperationalError as e:
        logger.warning(f"Could not retrieve K-line data, table might not exist yet: {e}")
        return JSONResponse(content=[]) # Return empty list so frontend doesn't break
    except Exception as e:
        logger.error(f"Failed to get K-line data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve K-line data.")

class KDataImportRequest(BaseModel):
    filename: str

@app.post("/api/import-kdata")
async def import_kdata_endpoint(request: KDataImportRequest):
    """Endpoint to trigger the K-line data import process for a specific file."""
    filename = request.filename
    logger.info(f"Received request to import K-line data from file: {filename}")
    try:
        summary_message = run_kdata_import(filename)
        logger.info(f"K-line data import process finished for {filename}. {summary_message}")
        return {"status": "success", "message": summary_message}
    except Exception as e:
        logger.critical(f"An unexpected error occurred during K-line data import for {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

@app.get("/api/trade_data")
async def get_trade_data(start_time: int, end_time: int):
    """
    API endpoint to retrieve trade data from the database within a specified time range.
    Returns full trade objects for charting markers and tooltips.
    """
    logger.info(f"TradeData Trace: Request received for trades between {start_time} and {end_time}.")
    try:
        conn = sqlite3.connect(DB_FILE)
        
        start_datetime_iso = datetime.fromtimestamp(start_time).isoformat(sep=' ', timespec='seconds')
        end_datetime_iso = datetime.fromtimestamp(end_time).isoformat(sep=' ', timespec='seconds')
        logger.info(f"TradeData Trace: Querying trades between ISO times {start_datetime_iso} and {end_datetime_iso}.")

        query = f"""
            SELECT
                t.trade_id,
                t.trade_time,
                t.action,
                t.net_pnl,
                t.contracts,
                COALESCE(md.close, (SELECT close FROM market_data WHERE datetime <= t.trade_time ORDER BY datetime DESC LIMIT 1)) as marker_price
            FROM
                trades t
            LEFT JOIN
                market_data md ON t.trade_time = md.datetime
            WHERE
                t.trade_time BETWEEN '{start_datetime_iso}' AND '{end_datetime_iso}'
            ORDER BY
                t.trade_time ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        logger.info(f"TradeData Trace: Read {len(df)} trade rows from the database.")

        if df.empty:
            logger.warning("TradeData Trace: No trades found for this time range, returning empty list.")
            return JSONResponse(content=[])

        df['trade_time'] = pd.to_datetime(df['trade_time'])
        df['time'] = df['trade_time'].astype('int64') // 10**9

        # Replace numpy NaN with None for JSON compatibility
        df.replace({np.nan: None}, inplace=True)
        
        # Select and rename columns for the final output
        output_df = df[[
            'time', 'action', 'contracts', 'net_pnl', 
            'marker_price'
        ]]

        trade_records = output_df.to_dict(orient='records')
        
        logger.info(f"TradeData Trace: Prepared {len(trade_records)} trade records to return.")
        return JSONResponse(content=trade_records)
        
    except sqlite3.OperationalError as e:
        logger.warning(f"Could not retrieve trade data, table might not exist yet: {e}")
        return JSONResponse(content=[])
    except Exception as e:
        logger.error(f"Failed to get trade data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve trade data.")


# --- Pydantic Models ---
class LogMessage(BaseModel):
    level: str
    message: str
    context: Optional[dict] = None

class RunCheckRequest(BaseModel):
    filename: str

class ImportRequest(BaseModel):
    filename: str

class TradeNote(BaseModel):
    trade_id: str
    note: Optional[str] = ""
    related_info: Optional[str] = ""

class TradeNoteList(BaseModel):
    trade_ids: List[str]

# --- CORS Middleware ---
# Allow requests from the Vue.js development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/trade_note")
async def save_trade_note(note: TradeNote):
    """Saves or updates a note for a specific trade."""
    logger.info(f"Received request to save note for trade_id: {note.trade_id}")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Use INSERT OR REPLACE to handle both new notes and updates
        cursor.execute("""
            INSERT OR REPLACE INTO trade_notes (trade_id, note, related_info, last_updated)
            VALUES (?, ?, ?, ?)
        """, (note.trade_id, note.note, note.related_info, datetime.now()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully saved note for trade_id: {note.trade_id}")
        return {"status": "success", "trade_id": note.trade_id}
    except Exception as e:
        logger.error(f"Failed to save note for trade_id {note.trade_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save trade note.")

@app.post("/api/trade_notes")
async def get_trade_notes(request: TradeNoteList):
    """Retrieves all notes for a given list of trade IDs."""
    logger.info(f"Received request to get notes for {len(request.trade_ids)} trades.")
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row # This allows accessing columns by name
        cursor = conn.cursor()

        # Use a parameterized query to avoid SQL injection
        placeholders = ','.join('?' for _ in request.trade_ids)
        if not placeholders:
            return JSONResponse(content={})
            
        cursor.execute(f"SELECT * FROM trade_notes WHERE trade_id IN ({placeholders})", request.trade_ids)
        
        notes = cursor.fetchall()
        conn.close()

        # Convert list of rows to a dictionary keyed by trade_id
        notes_dict = {row['trade_id']: dict(row) for row in notes}
        
        logger.info(f"Successfully retrieved {len(notes_dict)} notes.")
        return JSONResponse(content=notes_dict)
    except Exception as e:
        logger.error(f"Failed to retrieve notes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve trade notes.")

@app.post("/api/import_trades")
async def import_trades_from_file(request: ImportRequest):
    """Imports trades from a specified CSV file into the database."""
    filename = request.filename
    logger.info(f"Received request to import trades from file: {filename}")
    
    trade_file_path = os.path.join(TRADEDATA_DIRECTORY, filename)
    
    if not os.path.exists(trade_file_path):
        logger.error(f"File not found for import: {trade_file_path}")
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in 'tradedata' directory.")

    try:
        # Use a dummy auditor instance to process the file
        # We need to provide some dummy config values, although they are not used for loading
        temp_auditor = TradeAuditor(monthly_start_capital=0, current_scale="S1", operation_contracts=1)
        trades_df = temp_auditor.load_transactions_from_csv(trade_file_path)
        trades_df = temp_auditor._generate_trade_ids(trades_df)
        
        # Add source file information
        trades_df['source_file'] = filename
        
        # --- Insert into database ---
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        inserted_count = 0
        for _, row in trades_df.iterrows():
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO trades (trade_id, trade_time, action, net_pnl, contracts, product_name, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['trade_id'],
                    row['trade_time'].isoformat(),
                    row['action'],
                    row['net_pnl'],
                    row['contracts'],
                    row['product_name'],
                    row['source_file']
                ))
                if cursor.rowcount > 0:
                    inserted_count += 1
            except sqlite3.IntegrityError:
                # This can happen in rare race conditions, INSERT OR IGNORE is preferred
                logger.warning(f"Trade with ID {row['trade_id']} already exists. Skipping.")

        conn.commit()
        conn.close()
        
        total_rows = len(trades_df)
        skipped_count = total_rows - inserted_count
        
        summary_message = f"Import completed for '{filename}'. New trades: {inserted_count}, Skipped duplicates: {skipped_count}."
        logger.info(summary_message)
        return {"status": "success", "message": summary_message, "new": inserted_count, "skipped": skipped_count}
        
    except Exception as e:
        logger.error(f"Failed to import trades from {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to import trades: {str(e)}")

@app.get("/api/upgrade-criteria")
def get_upgrade_criteria():
    """
    API endpoint to retrieve the upgrade criteria.
    """
    logger.info("Request received for upgrade criteria.")
    return JSONResponse(content=UPGRADE_CRITERIA)

@app.get("/api/list_trade_files")
def get_trade_files():
    """
    API endpoint to list all available trade files in the 'tradedata' directory.
    """
    logger.info("Request received for trade files list.")
    try:
        files = list_trade_files(TRADEDATA_DIRECTORY)
        return JSONResponse(content={"files": files})
    except Exception as e:
        logger.error(f"Failed to list trade files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve trade files from server.")

# Helper function to convert numpy types to standard Python types
def convert_numpy_types(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

@app.post("/api/run_check")
async def run_check_for_file(request: RunCheckRequest):
    """
    Triggers a new audit based on a specific file from the 'tradedata' directory.
    This is the primary endpoint for the frontend.
    """
    filename = request.filename
    logger.info(f"Received request to run audit for file: {filename}")
    
    trade_file_path = os.path.join(TRADEDATA_DIRECTORY, filename)
    
    if not os.path.exists(trade_file_path):
        logger.error(f"File not found: {trade_file_path}")
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in 'tradedata' directory.")
        
    try:
        # --- Read configuration from config.ini ---
        config = configparser.ConfigParser()
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError(f"Configuration file '{CONFIG_FILE}' not found on server.")
        config.read(CONFIG_FILE)
        
        monthly_start_capital = config.getfloat('Account', 'monthly_start_capital')
        current_scale = config.get('Account', 'current_scale')
        operation_contracts = config.getint('Account', 'operation_contracts')

        # --- Initialize and run the auditor ---
        logger.info(f"Initializing auditor for scale {current_scale} with start capital {monthly_start_capital}")
        auditor = TradeAuditor(
            monthly_start_capital=monthly_start_capital,
            current_scale=current_scale,
            operation_contracts=operation_contracts
        )
        report = auditor.run_audit(filename)

        # --- Convert numpy types for JSON serialization ---
        json_compatible_report = convert_numpy_types(report)
        
        logger.info(f"Successfully ran audit and generated report for '{filename}'.")
        return JSONResponse(content=json_compatible_report)

    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Validation or file error during audit for {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except (configparser.Error, KeyError) as e:
        logger.error(f"Error parsing config file 'config.ini': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server configuration error: Could not read 'config.ini'.")
    except Exception as e:
        logger.critical(f"An unexpected server error occurred during check run for {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")


# Custom encoder for numpy types
custom_encoder = {
    np.integer: int,
    np.floating: float,
    np.ndarray: lambda x: x.tolist(),
    np.int64: int,
    np.float64: float
}

@app.post("/api/audit")
async def run_web_audit(
    monthly_start_capital: float = Form(...),
    current_scale: str = Form(...),
    file: UploadFile = File(...)
):
    """
    (Legacy) API endpoint to run the trade audit from an uploaded file.
    Accepts system parameters and a transaction file.
    """
    logger.info(f"Received audit request for uploaded file: {file.filename}")
    
    # This endpoint is now less critical but kept for potential direct uploads
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, file.filename)

    try:
        # --- Read operation_contracts from config.ini ---
        config = configparser.ConfigParser()
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError(f"Configuration file '{CONFIG_FILE}' not found on server.")
        config.read(CONFIG_FILE)
        operation_contracts = config.getint('DEFAULT', 'operation_contracts', fallback=1)
        logger.info(f"Loaded operation_contracts '{operation_contracts}' from {config_file}")

        # Save the uploaded file
        logger.info(f"Saving uploaded file to temporary path: {temp_file_path}")
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Initialize and run the auditor
        logger.info(f"Initializing auditor for scale {current_scale} with monthly start capital {monthly_start_capital}")
        auditor = TradeAuditor(
            monthly_start_capital=monthly_start_capital,
            current_scale=current_scale,
            operation_contracts=operation_contracts
        )
        report = auditor.run_audit(temp_file_path)
        
        logger.info(f"Audit successful for {file.filename}. Returning report.")
        json_compatible_report = jsonable_encoder(report, custom_encoder=custom_encoder)
        
        # Save the report to the main audit_report.json as well
        with open('audit_report.json', 'w', encoding='utf-8') as f:
            json.dump(json_compatible_report, f, ensure_ascii=False, indent=4)

        return JSONResponse(content=json_compatible_report)

    except (ValueError, FileNotFoundError) as e:
        # Handle known exceptions from the auditor (e.g., bad file, wrong scale, missing config)
        logger.error(f"Validation or file error during audit for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except configparser.Error as e:
        logger.error(f"Error parsing config file 'config.ini': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server configuration error: Could not read 'config.ini'.")
    except Exception as e:
        # Handle other unexpected errors
        logger.critical(f"An unexpected server error occurred during audit for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        # Clean up the uploaded file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"Cleaned up temporary file: {temp_file_path}")
        # Clean up the directory if it's empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")


@app.post("/api/log")
async def log_frontend_message(log: LogMessage):
    """
    API endpoint to receive and process log messages from the frontend.
    """
    # Map frontend log levels to Python logging levels
    level_map = {
        "info": logging.INFO,
        "warn": logging.WARNING,
        "error": logging.ERROR,
    }
    log_level = level_map.get(log.level.lower(), logging.INFO)

    # Format the log message to identify it as coming from the frontend
    log_prefix = "[Frontend]"
    full_message = f"{log_prefix} {log.message}"
    if log.context:
        full_message += f" | Context: {log.context}"

    logger.log(log_level, full_message)
    return {"status": "logged"}

@app.get("/api/status")
def get_status():
    """
    API endpoint to check if the backend server is running.
    """
    return {"status": "ok", "message": "TradeCheck backend is running"}

@app.get("/")
def read_root():
    return {"message": "TradeCheck Audit Backend is running. Use the /api/audit endpoint to post data."}

if __name__ == '__main__':
    logger.info("Starting TradeCheck backend server with uvicorn.")
    # This allows running the server directly for testing
    uvicorn.run(app, host="0.0.0.0", port=8000)
