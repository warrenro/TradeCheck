
import sqlite3
import os

DB_FILE = os.path.join('TradeCheck', 'trade_notes.db')
TABLE_NAME = 'market_data'

def check_data():
    if not os.path.exists(DB_FILE):
        print(f"資料庫檔案不存在: {DB_FILE}")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 檢查資料表是否存在
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}';")
        if cursor.fetchone() is None:
            print(f"資料表 '{TABLE_NAME}' 不存在於資料庫中。")
            return

        # 查詢資料筆數
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"資料庫中存在K線資料。'{TABLE_NAME}' 資料表中有 {count} 筆記錄。")
        else:
            print(f"資料庫中沒有K線資料。'{TABLE_NAME}' 資料表是空的。")
            
    except sqlite3.Error as e:
        print(f"查詢資料庫時發生錯誤: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    check_data()
