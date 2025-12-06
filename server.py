
import os
import shutil
import uvicorn
import logging
import configparser
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from fastapi.encoders import jsonable_encoder
import numpy as np

# Import the existing auditor class and the logger
from trade_check import TradeAuditor, logger, UPGRADE_CRITERIA

app = FastAPI()

# --- Pydantic Model for Frontend Logs ---
class LogMessage(BaseModel):
    level: str
    message: str
    context: Optional[dict] = None

# --- CORS Middleware ---
# Allow requests from the Vue.js development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Default port for Vite/Vue
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/upgrade-criteria")
def get_upgrade_criteria():
    """
    API endpoint to retrieve the upgrade criteria.
    """
    logger.info("Request received for upgrade criteria.")
    return JSONResponse(content=UPGRADE_CRITERIA)

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
    current_capital: float = Form(...),
    monthly_start_capital: float = Form(...),
    current_scale: str = Form(...),
    file: UploadFile = File(...)
):
    """
    API endpoint to run the trade audit.
    Accepts system parameters and a transaction file.
    """
    logger.info(f"Received audit request for file: {file.filename}")
    
    # Create a temporary directory to store the uploaded file
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, file.filename)

    try:
        # --- Read operation_contracts from config.ini ---
        config = configparser.ConfigParser()
        config_file = 'config.ini'
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found on server.")
        config.read(config_file)
        operation_contracts = config.getint('DEFAULT', 'operation_contracts', fallback=1)
        logger.info(f"Loaded operation_contracts '{operation_contracts}' from {config_file}")

        # Save the uploaded file
        logger.info(f"Saving uploaded file to temporary path: {temp_file_path}")
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Initialize and run the auditor
        logger.info(f"Initializing auditor for scale {current_scale} with capital {current_capital}")
        auditor = TradeAuditor(
            current_capital=current_capital,
            monthly_start_capital=monthly_start_capital,
            current_scale=current_scale,
            operation_contracts=operation_contracts
        )
        report = auditor.run_audit(temp_file_path)
        
        logger.info(f"Audit successful for {file.filename}. Returning report.")
        json_compatible_report = jsonable_encoder(report, custom_encoder=custom_encoder)
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
