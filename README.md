
# D-Pro Protocol V7.3 自動化審計系統 (Automated Audit System)

本專案旨在自動化執行《D-Pro Protocol V7.3》之風控與激勵審查。系統結合使用者輸入的交易紀錄與帳戶狀態，自動運算是否觸發**風控熔斷**、**升降級審查**及**幸福激勵**等機制，並提供清晰的審計報告。

此專案包含兩種操作模式：
1.  **指令碼模式 (Command-Line)**: 直接執行 Python 腳本進行分析。
2.  **網頁介面模式 (Web UI)**: 透過 Vue.js 前端與 FastAPI 後端，提供友善的使用者介面進行操作。

---

## 核心功能 (Features)

- **儀表板介面 (Dashboard UI)**: 使用現代化的儀表板呈現審計報告，包含 KPI 卡片、狀態面板等，讓數據一目了然。
- **多國語系支援 (Multi-Language)**: 支援繁體中文與英文介面，可即時切換。
- **自動化 KPI 計算**:
  - **勝率 (Win Rate)**
  - **賺賠比 (Risk/Reward Ratio)**
- **風險剎車機制 (Safety Valves)**:
  - **日內風控**: 監控當日虧損次數是否超過 3 次。
  - **月度熔斷**: 監控當月虧損是否超過初始資金的 15%。
- **夜盤戰略合規性檢查**:
  - 檢查是否在**美股開盤**或 **FOMC 公布**的避險時段內進行交易。
- **資金控管審查 (Capital Management)**:
  - **雙鑰匙升級**: 根據本金與績效表現，判斷是否符合下一規模的升級資格。
  - **強制降級條款**: 檢查是否觸發降級條件。
- **生活與戰略規則**:
  - **護城河鐵律**: 判斷是否處於獲利鎖定期。
  - **幸福激勵**: 在滿足條件下，自動計算可提領的激勵金額。

---

## 技術棧 (Tech Stack)

- **後端 (Backend)**: Python, FastAPI, Pandas
- **前端 (Frontend)**: Vue.js (v3), Vite, JavaScript, vue-i18n
- **核心邏輯 (Core Logic)**: Python

---

## 安裝與啟動 (Installation & Usage)

### 先決條件 (Prerequisites)
請確保您的系統已安裝：
- [Python](https://www.python.org/downloads/) (3.8 或更高版本)
- [Node.js](https://nodejs.org/) (16.x 或更高版本)

### 模式一：網頁介面 (Web UI)

您需要開啟兩個終端機視窗來分別啟動後端與前端服務。

**➡️ 終端機 1: 啟動後端 (Backend)**

1.  **安裝/更新 Python 依賴套件:**
    ```bash
    pip install --upgrade -r requirements.txt
    ```

2.  **啟動 FastAPI 後端伺服器:**
    ```bash
    uvicorn server:app --reload
    ```
    後端服務將會運行在 `http://localhost:8000`。

**➡️ 終端機 2: 啟動前端 (Frontend)**

1.  **進入 `frontend` 目錄:**
    ```bash
    cd frontend
    ```

2.  **安裝 Node.js 依賴套件:**
    ```bash
    npm install
    ```

3.  **啟動 Vite 前端開發伺服器:**
    ```bash
    npm run dev
    ```
    前端應用將會運行在 `http://localhost:5173`。

4.  **開啟瀏覽器**並訪問 `http://localhost:5173`，即可開始使用。

### 模式二：指令碼 (Command-Line)

如果您只想使用原始的 Python 指令碼進行分析：

1.  **安裝/更新 Python 依賴套件:**
    ```bash
    pip install --upgrade -r requirements.txt
    ```

2.  **執行 Python 指令碼:**
    ```bash
    python trade_check.py
    ```
    此指令碼會使用內建的範例資料 (`dummy_trades.csv`) 執行三次模擬分析，並將結果輸出到終端機。您可以直接修改 `trade_check.py` 的 `if __name__ == '__main__':` 區塊來載入您自己的交易檔案和參數。

---

## 檔案結構 (Project Structure)

```
TradeCheck/
├── frontend/              # Vue.js 前端應用程式
│   ├── src/
│   │   ├── App.vue        # 主要 UI 元件
│   │   └── main.js      # 前端進入點
│   ├── index.html         # HTML 主頁
│   └── package.json       # 前端依賴套件定義
├── trade_check.py         # 核心審計邏輯
├── server.py              # FastAPI 後端伺服器
├── requirements.txt       # Python 依賴套件
├── spec.md                # 原始系統規格書
└── README.md              # 本說明文件
```
