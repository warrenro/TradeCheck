import os
import glob
import pandas as pd
import sqlite3
import logging

# --- Configuration ---
# 設定日誌記錄，方便追蹤執行狀況
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Dynamic Path Configuration ---
# Get the absolute path of the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Build absolute paths to the database and KData directory
DB_PATH = os.path.join(SCRIPT_DIR, 'trade_notes.db')
KDATA_DIR = os.path.join(SCRIPT_DIR, 'KData')
TABLE_NAME = 'market_data'
# --- End Configuration ---

def create_connection(db_file):
    """建立並返回一個 SQLite 資料庫連線"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        logging.info(f"成功連接到資料庫: {db_file}")
    except sqlite3.Error as e:
        logging.error(f"資料庫連線失敗: {e}")
    return conn

def create_market_data_table(conn):
    """如果 market_data 資料表不存在，則建立該表"""
    # 使用 IF NOT EXISTS 避免重複建立
    # 將 datetime 設為 PRIMARY KEY，以確保資料的唯一性
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        datetime TEXT PRIMARY KEY,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume INTEGER NOT NULL
    );
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
        logging.info(f"資料表 '{TABLE_NAME}' 已成功準備就緒。")
    except sqlite3.Error as e:
        logging.error(f"建立資料表失敗: {e}")

def import_csv_to_db(conn, csv_file_path):
    """
    Reads a single CSV file and imports its content into the database.
    Returns the number of new rows inserted and duplicate rows skipped.
    """
    try:
        logging.info(f"Reading file: {os.path.basename(csv_file_path)}")
        df = pd.read_csv(csv_file_path)

        column_mapping = {
            'Time': 'datetime', 'Datetime': 'datetime', '時間': 'datetime',
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
            '開盤價': 'open', '最高價': 'high', '最低價': 'low', '收盤價': 'close', '成交量': 'volume'
        }
        df.rename(columns=column_mapping, inplace=True)

        required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            logging.error(f"File {os.path.basename(csv_file_path)} is missing required columns. Skipping. "
                          f"Required: {required_cols}, Found: {df.columns.tolist()}")
            return 0, 0

        rows_to_insert = df[required_cols].to_records(index=False).tolist()
        
        if not rows_to_insert:
            logging.warning(f"File {os.path.basename(csv_file_path)} contains no data to import.")
            return 0, 0
            
        cursor = conn.cursor()
        
        insert_sql = f"INSERT OR IGNORE INTO {TABLE_NAME} (datetime, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?)"
        
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        initial_row_count = cursor.fetchone()[0]

        cursor.executemany(insert_sql, rows_to_insert)
        conn.commit()

        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        final_row_count = cursor.fetchone()[0]
        
        inserted_rows = final_row_count - initial_row_count
        skipped_rows = len(rows_to_insert) - inserted_rows

        logging.info(f"Processed {os.path.basename(csv_file_path)}: "
                     f"New rows: {inserted_rows}, "
                     f"Skipped duplicates: {skipped_rows}.")
        return inserted_rows, skipped_rows

    except pd.errors.EmptyDataError:
        logging.warning(f"File {csv_file_path} is empty. Skipping.")
        return 0, 0
    except Exception as e:
        logging.error(f"An error occurred while importing file {csv_file_path}: {e}")
        return 0, 0

def run_kdata_import(filename: str = None):
    """
    Orchestrates the K-line data import process.
    If a filename is provided, it imports only that file. Otherwise, it imports all CSV files
    from the KData directory.
    Returns a summary message of the operation.
    """
    logging.info(f"===== Starting K-line data import task (File: {filename or 'All'}) =====")
    
    conn = create_connection(DB_PATH)
    if conn is None:
        error_msg = "Database connection failed, aborting import task."
        logging.error(error_msg)
        return error_msg

    total_files = 0
    total_new_rows = 0
    total_skipped_rows = 0

    with conn:
        create_market_data_table(conn)
        
        files_to_process = []
        if filename:
            # Prevent directory traversal attacks
            safe_path = os.path.abspath(os.path.join(KDATA_DIR, filename))
            if not safe_path.startswith(os.path.abspath(KDATA_DIR)):
                error_msg = f"Error: Invalid filename, potential directory traversal: {filename}"
                logging.error(error_msg)
                return error_msg
            
            if os.path.exists(safe_path) and safe_path.endswith('.csv'):
                files_to_process.append(safe_path)
            else:
                warning_msg = f"Specified file not found or not a CSV: {filename}"
                logging.warning(warning_msg)
                return warning_msg
        else:
            # Original behavior: process all CSV files
            files_to_process = glob.glob(os.path.join(KDATA_DIR, '*.csv'))

        total_files = len(files_to_process)
        
        if not files_to_process:
            warning_msg = f"No CSV files found to import in '{KDATA_DIR}'."
            logging.warning(warning_msg)
            return warning_msg

        logging.info(f"Found {total_files} CSV file(s) to import.")
        
        for csv_file in sorted(files_to_process):
            new, skipped = import_csv_to_db(conn, csv_file)
            total_new_rows += new
            total_skipped_rows += skipped

    summary_message = (f"K-line data import finished. Processed {total_files} file(s). "
                       f"New records: {total_new_rows}, Skipped duplicates: {total_skipped_rows}.")
    logging.info(summary_message)
    return summary_message


def main():
    """Main execution function for standalone script usage."""
    result_message = run_kdata_import()
    print(result_message)

if __name__ == '__main__':
    main()
