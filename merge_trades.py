
import pandas as pd
import sqlite3
import logging
from datetime import datetime

# --- Configuration ---
DB_FILE = 'trade_notes.db'
TRADES_TABLE = 'trades'
TRANSACTION_DATA_TABLE = 'TransactionData'
MERGED_TABLE = 'trades_merged'

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def merge_trade_data():
    """
    Merges trade data with transaction data to backfill the open trade time.
    """
    logger.info(f"Connecting to database: {DB_FILE}")
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Load data from tables
        logger.info(f"Loading data from '{TRADES_TABLE}' and '{TRANSACTION_DATA_TABLE}' tables...")
        trades_df = pd.read_sql_query(f"SELECT * FROM {TRADES_TABLE}", conn)
        transactions_df = pd.read_sql_query(f"SELECT * FROM {TRANSACTION_DATA_TABLE}", conn)
        logger.info(f"Loaded {len(trades_df)} records from '{TRADES_TABLE}'.")
        logger.info(f"Loaded {len(transactions_df)} records from '{TRANSACTION_DATA_TABLE}'.")

    except Exception as e:
        logger.error(f"Failed to read data from database: {e}", exc_info=True)
        return

    if trades_df.empty:
        logger.warning(f"The '{TRADES_TABLE}' table is empty. No data to process.")
        return
        
    if transactions_df.empty:
        logger.warning(f"The '{TRANSACTION_DATA_TABLE}' table is empty. Cannot find open times.")
        return

    # --- Data Preparation ---
    # Convert time columns to datetime objects for comparison
    trades_df['trade_time'] = pd.to_datetime(trades_df['trade_time'])
    transactions_df['transaction_time'] = pd.to_datetime(transactions_df['transaction_time'])

    # Separate opening transactions for faster lookup
    opening_transactions = transactions_df[transactions_df['position_type'] == '新倉'].copy()
    
    if opening_transactions.empty:
        logger.warning("No opening trades ('新倉') found in 'TransactionData'. Cannot proceed.")
        return
        
    # --- Matching Logic ---
    open_times = []
    match_count = 0

    logger.info("Starting to match open times for each PnL record...")
    for _, pnl_record in trades_df.iterrows():
        close_time = pnl_record['trade_time']
        open_price = pnl_record['open_price']
        product = pnl_record['product_name']

        # Filter for candidate opening trades based on logic
        candidates = opening_transactions[
            (opening_transactions['product_name'].str.contains(product, na=False)) &
            (opening_transactions['price'] == open_price) &
            (opening_transactions['transaction_time'] < close_time)
        ]

        if not candidates.empty:
            # Calculate time difference and find the closest one
            candidates['time_diff'] = close_time - candidates['transaction_time']
            best_match = candidates.loc[candidates['time_diff'].idxmin()]
            open_times.append(best_match['transaction_time'])
            match_count += 1
        else:
            # If no match is found
            open_times.append(None)

    # Add the new column to the DataFrame
    trades_df['open_trade_time'] = open_times
    
    # Convert datetime objects to string format for SQLite
    trades_df['open_trade_time'] = trades_df['open_trade_time'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('N/A')
    trades_df['trade_time'] = trades_df['trade_time'].dt.strftime('%Y-%m-%d %H:%M:%S')


    logger.info(f"Matching process complete. Found open times for {match_count} out of {len(trades_df)} records.")

    # --- Save to Database ---
    try:
        logger.info(f"Writing merged data to new table: '{MERGED_TABLE}'...")
        trades_df.to_sql(MERGED_TABLE, conn, if_exists='replace', index=False)
        logger.info(f"Successfully saved {len(trades_df)} records to '{MERGED_TABLE}' table.")

    except Exception as e:
        logger.error(f"Failed to write merged data to database: {e}", exc_info=True)
    finally:
        conn.close()
        logger.info("Database connection closed.")


if __name__ == '__main__':
    logger.info("="*50)
    logger.info("Starting Trade Data Merging Script")
    logger.info("="*50)
    merge_trade_data()
    logger.info("Script finished.")

