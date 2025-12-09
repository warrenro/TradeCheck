# TradeCheck 系統實作與設計決策
- **版本**: v2.4
- **最後更新日期**: 2025-12-09

本文檔旨在記錄 `TradeCheck` 專案在根據 `spec.md` 進行功能開發時，其核心功能的實作摘要、關鍵的設計決策與問題修正過程。它並非鉅細靡遺的步驟紀錄，而是為了幫助未來的維護者快速理解系統的設計思路與重要權衡。

---
(Sections 1 to 4 remain unchanged)
...
---

## 5. K線圖顯示功能實作 (Candlestick Chart Display Implementation)

為了將 K 線資料視覺化，我們引入了 `lightweight-charts` 函式庫來顯示互動式圖表。

### 5.1 後端 API 設計 (`server.py`)

- **新增 `GET /api/kline_data` API**:
  - **目的**: 提供格式化後的 K 線資料給前端圖表使用。
  - **實作**:
    1. API 連線至 `trade_notes.db` 資料庫。
    2. 查詢 `market_data` 資料表，選取 `Datetime`, `Open`, `High`, `Low`, `Close`, `Volume` 欄位。
    3. 將查詢結果的 `Datetime` 欄位轉換為 UNIX 時間戳（秒），並將欄位重命名為 `time`, `open`, `high`, `low`, `close`, `value` 以符合 `lightweight-charts` 的資料格式。
    4. 回傳一個 JSON 陣列給前端。

### 5.2 前端實作 (`frontend/src/`)

- **安裝圖表庫**:
  - 於 `frontend` 目錄下執行 `npm install lightweight-charts`。

- **新增 `KlineChart` 元件**:
  - 此元件負責：
    1.  在掛載時 (`onMounted`) 呼叫後端的 `/api/kline_data` API 來獲取圖表資料。
    2.  使用 `lightweight-charts` API 來初始化圖表，設定圖表外觀（如背景色、格線）。
    3.  建立一個 K 線序列 (Candlestick Series) 並將獲取到的價格資料設定進去。
    4.  建立一個成交量序列 (Histogram Series) 並將獲取到的成交量資料設定進去。
    5.  處理圖表容器的 resizing，確保圖表在視窗大小改變時能自適應。

- **整合至主畫面 (`App.vue`)**:
  - 在 `App.vue` 中新增一個「行情圖表」的分頁標籤。
  - 當使用者切換到此分頁時，渲染 `KlineChart.vue` 元件。

### 5.3 交易資料圖層實作 (Trade Data Layer Implementation)

為了在 K 線圖上疊加顯示交易資料，我們在後端新增了 API 並在前端 `KlineChart.vue` 中進行了整合。

- **後端 API (`server.py`)**:
  - **新增 `GET /api/trade_data` API**:
    - **目的**: 提供指定時間範圍內的交易紀錄給前端，並包含標記所需的價格資訊。
    - **實作**:
      1. API 接收 `start_time` 和 `end_time` (Unix timestamp) 參數。
      2. 連接至 `trade_notes.db` 資料庫，查詢 `trades` 表以獲取在時間範圍內的交易紀錄。
      3. 為了獲取每個交易發生時的價格，API 會嘗試將 `trades` 表與 `market_data` 表透過 `trade_time` 進行 `LEFT JOIN`。若沒有精確匹配的 K 線資料，則會尋找最接近該交易時間點的 K 線 `close` 價格。
      4. 將交易時間轉換為 UNIX 時間戳（秒）。
      5. 返回一個 JSON 陣列，每個元素都是一個 `lightweight-charts` 格式的 Marker 物件，包含 `time`, `price`, `action` (用於決定箭頭方向和顏色), 以及 `text` (顯示交易詳情，如買賣別、數量和價格)。

- **前端實作 (`KlineChart.vue`)**:
  - **狀態管理**:
    - 新增 `showTradeData` (boolean ref) 用於控制交易圖層的顯示/隱藏。
    - 新增 `tradeData` (array ref) 用於儲存從後端獲取的交易資料。
  - **工具列整合**:
    - 在圖表工具列新增一個「交易資料」Checkbox，綁定 `showTradeData`。
  - **資料獲取**:
    - 實作 `fetchTradeData(startTime, endTime)` 非同步函數，專責呼叫後端 `/api/trade_data` API。
  - **圖層繪製**:
    - 實作 `drawTradeData()` 函數：
      - 判斷 `showTradeData.value` 和 `tradeData.value.length > 0`。
      - 將 `tradeData` 映射成 `lightweight-charts` 所需的 `marker` 格式：
        - `time`: 交易時間的 UNIX 時間戳。
        - `position`: 根據買賣別 (`buy` 為 `belowBar`，`sell` 為 `aboveBar`) 決定標記位置。
        - `color`: 根據買賣別設定綠色 (買) 或紅色 (賣)。
        - `shape`: 根據買賣別設定向上 (`arrowUp`) 或向下 (`arrowDown`) 箭頭。
        - `text`: 後端提供的交易詳情文字。
      - 使用 `candlestickSeries.setMarkers(markers)` (或 `lineSeries.setMarkers(markers)`) 將標記繪製到主圖系列上。
      - 若 `showTradeData.value` 為 `false` 或 `tradeData` 為空，則呼叫 `setMarkers([])` 清空標記。
  - **生命週期與資料更新**:
    - 在 `onMounted` 鉤子中，初始化圖表後，首次呼叫 `fetchTradeData` 和 `drawTradeData`。
    - 在 `updateChartData` 函數中，每次時間週期改變或 K 線資料更新後，重新呼叫 `fetchTradeData` 和 `drawTradeData`，確保交易資料與 K 線資料同步更新。

---

## 1. 核心功能實作摘要 (Core Feature Implementation Summary)

為了實現 `spec.md` 中定義的複雜分析與審計功能，`trade_check.py` 腳本的核心邏輯被組織成一系列獨立的函式，並由主函式 `run_audit` 進行統籌調用。以下是關鍵模組的職責劃分：

- **`config.ini` 整合**:
  - 程式啟動時會讀取 `config.ini`，獲取 `月初本金`、`操作規模` 等使用者自定義參數。`目前權益數` 則根據 `月初本金` 和當月損益動態計算，實現了設定與程式碼的分離。

- **`monthly_start_capital` 報告輸出**:
  - `trade_check.py` 已將 `monthly_start_capital` 加入到審計報告的 `account_summary` 區塊，以供前端介面顯示。

- **`_calculate_annual_summary` (年度總結計算)**:
  - 此方法現已修改為針對每個交易年份獨立計算其總體損益、勝率、賺賠比及總交易筆數，並將結果包含在審計報告中，以支援前端的年度總結區塊分年顯示。

- **`load_transactions` (資料讀取)**:
  - 負責讀取 `tradedata/` 目錄下的交易紀錄，並驗證 `成交時間`, `買賣別`, `平倉損益淨額`, `口數`, `商品名稱` 等必要欄位是否存在。

- **`_add_trade_points_column` (計算交易點數)**:
  - 根據 `商品名稱` 決定點值 (50/10/200)，計算每筆交易的「點數」 (`points`)，作為交易 DNA 診
斷的基礎。

- **`_run_trading_dna_diagnosis` (交易 DNA 診斷)**:
  - 依據 `points` 將交易劃分為「噪音區」(`<=40點`) 與「波段區」(`>40點`)。
  - 獨立計算兩個區間的交易筆數、勝率、總損益，並根據 `spec.md` 的規則判斷使用者是否「陷入泥淖」。

- **`_run_sop_risk_stress_test` (SOP 風險壓力測試)**:
  - 基於固定的 `1500` 最大曝險點數，計算在當前操作規模下的潛在風險值與風險率，並在 `風險率 > 15%` 時生成警告。

- **`_check_safety_valves` (D-Pro 風險審計)**:
  - 實作了多項 D-Pro 風險規則，包括「日內風控」、「月度資金熔斷」及「月度策略熔斷」。

- **`_check_night_session` (夜盤避險時段檢查)**:
  - 檢查是否有任何交易的 **平倉時間** 落入 `21:15-21:45` 或 `01:45-02:15` 區間，以執行夜盤避險規則。(*細節請參考 2.4 節*)

- **`_evaluate_capital_management` (帳戶升級評估)**:
  - 在 **3, 6, 9, 12 月**進行評估時，會從`目前權益數`中扣除 **25,000** 元的「季度固定成本」。
  - 根據調整後的資本額、風報比與勝率，與 `UPGRADE_CRITERIA` 比對，判斷是否符合升級資格。

- **`run_audit` (主審計流程)**:
  - 作為主流程函式，依序調用上述所有分析與審計模組。
  - 最終將所有結果彙整成一個字典，並寫入 `audit_report.json` 檔案。

---

## 2. 除錯與關鍵決策 (Debugging and Key Decisions)

在開發與整合過程中，有數個關鍵的技術問題與邏輯釐清，其解決方案對系統的穩定性與正確性至關重要。

### 2.1 錯誤一：伺服器 API 呼叫失敗

- **錯誤現象**: 前端呼叫 API 時，伺服器日誌顯示 `TypeError: TradeAuditor.__init__() missing 1 required positional argument: 'operation_contracts'`。
- **根本原因**: `trade_check.py` 的 `TradeAuditor` 類別在 `__init__` 中新增了 `operation_contracts` 參數，但 `server.py` 的 API 端點在呼叫它時未同步更新。
- **解決方案**: 修改 `server.py`，使其在 API 內部也讀取 `config.ini`，從中獲取 `operation_contracts` 並在建立 `TradeAuditor` 物件時傳入，確保前後端模組介面一致。

### 2.2 錯誤二：JSON 序列化失敗 - `float('inf')`

- **錯誤現象**: API 呼叫日誌顯示 `ValueError: Out of range float values are not JSON compliant`。
- **根本原因**: 當交易紀錄中沒有虧損時，「賺賠比」的計算結果為 `float('inf')` (無限大)，此數值不符合 JSON 標準。
- **解決方案**:
    1.  修改 `_calculate_kpis` 和 `_run_sop_risk_stress_test` 函式，將回傳 `float('inf')` 的情況改為回傳 **字串** `"Infinity"`。
    2.  同步修改下游使用這些值的函式 (`_evaluate_capital_management` 等)，使其能夠正確處理 `"Infinity"` 這個字串，通常是視為滿足績效標準。

### 2.3 錯誤三：JSON 序列化失敗 - `f-string` 格式化

- **錯誤現象**: 即使修正了 `inf` 問題，序列化失敗的錯誤依然存在。
- **根本原因**: 在 `run_audit` 中，使用了 f-string `f"{rr:.2f}"` 來格式化賺賠比 `rr`。當 `rr` 的值是 `"Infinity"` 字串時，此格式化操作會引發 `ValueError`。
- **解決方案**: 在格式化輸出前加入條件判斷，確保只有在變數是數字時才進行格式化，如果是字串則直接使用。
    ```python
    # 修正後的寫法
    "risk_reward_ratio": rr if isinstance(rr, str) else f"{rr:.2f}"
    ```

### 2.4 規則邏輯釐清：「夜盤避險時段」的實作

- **規則模糊點**: `spec.md` 要求「禁止開立新倉」，但系統僅有「平倉資料」，無法直接獲取「開倉時間」。
- **問題**: 如何在只有平倉資料的情況下，準確執行此規則？
- **最終決策與權衡**:
    1.  **確認資料本質**: 提供的交易紀錄是「平倉資料」，`成交時間` 代表「平倉時間」。
    2.  **推斷規則意圖**: 此規則的風控本質是「**確保在敏感時段內無任何交易活動風險**」。
    3.  **最終實作**: 考量到資料限制，`_check_night_session` 函式的最終邏輯被確定為：檢查 **所有交易的平倉時間**。只要有任何一筆交易的平倉時間落入指定區間，即視為違規。此作法確保了使用者在避險時段內已完全清倉，達成了規則的實質目的。函式文件也已同步更新，以反映此判斷邏輯。

### 2.5 錯誤五：前端畫面無法顯示審計報告

- **錯誤現象**: 前端成功呼叫 API 並取得數據後，畫面並未渲染出審計報告，而是停留在初始狀態。
- **根本原因**: `TradeCheck/frontend/src/App.vue` 檔案中，月度總結表格的資料綁定路徑有誤。程式碼嘗試存取 `summary.incentive.amount` 來顯示激勵獎金，但根據後端 API 回傳的資料結構，正確的路徑應為 `summary.happiness_incentive.amount`。這個錯誤的路徑導致 Vue 在渲染時拋出執行階段錯誤，中斷了畫面的更新。
- **解決方案**:
    1.  **定位問題**: 檢查瀏覽器開發者主控台，發現 Vue 的渲染錯誤，指向 `App.vue` 範本中的一個屬性存取問題。
    2.  **修正路徑**: 將範本中的 `formatCurrency(summary.incentive.amount)` 修改為 `formatCurrency(summary.happiness_incentive.amount)`，使其與 `historical_summary` 物件的資料結構保持一致。
- **影響**: 此修正恢復了前端的渲染能力，確保 API 回傳的報告能夠被正確地呈現在使用者介面中。

### 2.6 錯誤六：後端資料處理與序列化錯誤

在處理特定資料檔案時，系統發生了兩類主要的後端錯誤，導致審計流程中斷。

- **錯誤現象一**: 伺服器日誌顯示 `TypeError: argument of type 'float' is not iterable`。
- **根本原因一**:
    此錯誤發生在 `_add_trade_points_column` 函式內部調用的 `calculate_points` 方法中。當交易紀錄 CSV 檔案的 `商品名稱` (`product_name`) 欄位有缺失值 (空值) 時，Pandas 會將其讀取為 `NaN` (Not a Number)，其資料型別為 `float`。後續的程式碼嘗試對這個 `float` 型別的 `product_name` 進行字串匹配迭代，從而引發 `TypeError`。
- **解決方案一**:
    在 `calculate_points` 函式中，對傳入的 `product_name` 進行型別檢查與轉換。在進行迭代匹配之前，先確保它是一個字串。如果值為 `NaN` 或其他非字串類型，則將其視為空字串，避免了迭代錯誤，並使其能夠安全地走完流程（雖然可能找不到對應的點值）。

- **錯誤現象二**: API 呼叫日誌顯示 `ValueError: [TypeError("'numpy.int64' object is not iterable"), TypeError('vars() argument must have __dict__ attribute')]`。
- **根本原因二**:
    此錯誤發生在 `server.py` 將審計報告回傳給前端的過程中。Pandas 在進行數據聚合時，產生的數值（如交易筆數、總損益等）其資料型別通常是 NumPy 的特定型別，例如 `numpy.int64` 或 `numpy.float64`。FastAPI 預設的 `jsonable_encoder` 無法直接將這些 NumPy 特有的數字型別序列化為標準的 JSON 格式，從而導致轉換失敗。
- **解決方案二**:
    在 `server.py` 中，將 `run_audit` 產生的報告傳遞給 `jsonable_encoder` 之前，手動將報告中的所有 NumPy 數值型別轉換為標準的 Python 型別 (如 `int`, `float`)。我實作了一個遞迴函式 `convert_numpy_types` 來遍歷整個報告字典（包括巢狀的字典和列表），並轉換所有 `numpy.integer` 和 `numpy.floating` 的實例。
- **影響**: 這兩項修正強化了系統的穩定性（魯棒性），使其能夠應對不乾淨的輸入資料（如缺失的商品名稱）以及處理 Python 生態系統中常見的 NumPy 資料型別，確保了 API 的正常回應與前後端資料流的順暢。經過這些修正，後端系統的核心錯誤皆已解決，應用程式現已進入穩定狀態。

---

## 3. 架構演進：資料庫化與備註功能 (Architectural Evolution: Databasing and Annotation Feature)

為了支援更複雜的跨檔案查詢與交易備註功能，專案架構進行了一次重大升級，從「每次分析時動態讀取 CSV」演變為「以 SQLite 資料庫為核心資料來源」。

### 3.1 資料庫初始化 (`server.py`)
- **啟動時檢查**: 伺服器在啟動時 (`@app.on_event("startup")`) 會自動執行 `init_database` 函式。
- **建立資料表**: 該函式會檢查並建立 `trade_notes.db` 資料庫檔案，並確保其中包含兩個核心資料表：
  - `trades`: 用於儲存從 CSV 匯入的所有交易紀錄。
  - `trade_notes`: 用於儲存使用者為每筆交易新增的備註。

### 3.2 核心邏輯重構 (`trade_check.py`)
- **資料來源變更**: `TradeAuditor` 類別的核心方法 `run_audit` 不再接收檔案路徑，而是接收 `source_file` (來源檔名) 作為篩選條件。
- **新增資料庫讀取方法**: `run_audit` 內部不再呼叫 `load_transactions` (從 CSV 讀取)，而是呼叫新的 `load_transactions_from_db` 方法。
- **`load_transactions_from_db`**: 此方法負責連接到 SQLite 資料庫，並根據傳入的 `source_file` 參數，`SELECT` 出對應的交易紀錄，再將其轉換為與舊版輸出格式完全一致的 Pandas DataFrame。這個設計確保了下游的所有計算函式 (`_calculate_kpis`, `_check_safety_valves` 等) 無需任何修改即可繼續運作。

### 3.3 後端 API 設計 (`server.py`)

#### a. `POST /api/import_trades` (匯入交易)
- **目的**: 提供一個標準化流程，將 CSV 檔案中的交易紀錄匯入資料庫。
- **實作**: 
  1. 後端接收到帶有 `filename` 的請求。
  2. 為了重用 `trade_check.py` 中成熟的資料清洗與 `trade_id` 生成邏輯，API 內部會建立一個暫時的 `TradeAuditor` 實例來處理 CSV 檔案。
  3. API 遍歷處理後的 DataFrame，並使用 `INSERT OR IGNORE INTO trades ...` SQL 指令將交易寫入資料庫。`OR IGNORE` 確保了如果 `trade_id` 已存在（代表這筆交易之前已被匯入），資料庫會直接忽略，從而避免了重複紀錄的問題。
  4. 回傳包含新增及跳過筆數的摘要給前端。

#### b. `POST /api/trade_note` & `POST /api/trade_notes` (備註管理)
- **儲存備註**: 前端呼叫 `POST /api/trade_note`，後端使用 `INSERT OR REPLACE` 語法，這使得同一筆交易的備註可以被多次新增或覆蓋更新，操作上更為直覺。
- **讀取備註**: 前端在開啟月度明細時，會收集該月所有交易的 `trade_id`，並一次性透過 `POST /api/trade_notes` 請求所有備註。後端回傳一個以 `trade_id` 為鍵的字典，供前端快速查找與顯示，避免了逐筆請求的效能問題。

### 3.4 前端互動流程 (`App.vue`)
- **雙按鈕設計**: 在檔案選擇器下方，設計了「匯入此檔案」和「開始分析」兩個獨立按鈕，讓使用者可以明確控制操作流程。
- **匯入流程**: 使用者點擊「匯入」，觸發 `/api/import_trades` API，並透過 `alert` 接收簡單的結果回饋。
- **分析流程**: 使用者點擊「開始分析」，觸發 `/api/run_check` API。後端 `run_check` 現在會從資料庫撈取資料進行分析。
- **備註流程**:
  1. 使用者在月度總結表格點擊某個月，觸發 `showMonthDetails`。
  2. `showMonthDetails` 收集該月所有 `trade_id`，呼叫 `/api/trade_notes` 取得備註資料。
  3. 使用者在明細彈窗中點擊「編輯」，觸發 `openEditNoteModal`，並在編輯視窗中修改內容。
  4. 點擊「儲存」觸發 `saveNote` 函式，呼叫 `/api/trade_note` 將備註儲存至後端資料庫，並在成功後即時更新前端畫面。
  5. `closeMonthDetails` 函式會清空 `tradeNotes` 狀態，確保下次開啟其他月份時不會顯示舊資料。

---

## 4. K線資料匯入功能實作 (K-Line Data Import Implementation)

為了將交易紀錄與市場行情資料結合，系統新增了 K 線資料的匯入與儲存功能，並採用了前後端分離的互動模式。

### 4.1 資料庫擴充 (`init_database` in `server.py`)
- **新增 `market_data` 資料表**: 在 `init_database` 函式中，新增了建立 `market_data` 資料表的邏輯。
  - **結構**: 包含 `Datetime`, `Open`, `High`, `Low`, `Close`, `Volume` 等標準 K 線欄位。
  - **主鍵**: `Datetime` 欄位被設為 `PRIMARY KEY`，利用 `INSERT OR IGNORE` 指令來防止重複的行情資料被寫入。

### 4.2 後端 API 設計 (`server.py`)

#### a. `GET /api/kdata_files` (獲取 K 線檔案列表)
- **目的**: 讓前端能動態獲取 `KData/` 目錄下所有可用的 K 線資料檔案。
- **實作**: 
  1. 此 API 端點會掃描 `KData/` 目錄。
  2. 回傳一個包含所有 `.csv` 檔名的 JSON 列表給前端。

#### b. `POST /api/import_kdata` (匯入指定的 K 線檔案)
- **目的**: 接收前端傳來的特定檔名，並執行該檔案的匯入作業。
- **實作**:
  1. API 接收一個包含 `filename` 的 JSON payload。
  2. 為了安全性，會驗證 `filename` 是否為一個合法的檔名且存在於 `KData/` 目錄下。
  3. API 調用 `import_kdata.py` 腳本中的核心匯入函式，並將 `filename` 作為參數傳入。
  4. 執行完成後，回傳一個 JSON 響應，告知前端成功匯入的檔案名稱與新增的資料筆數。

### 4.3 後端腳本 (`import_kdata.py`)
- **由掃描改為接收參數**: 腳本的核心匯入函式被重構，不再自行掃描目錄，而是接收一個 `file_path` 作為參數。
- **讀取與標準化**: 
  - 腳本根據傳入的 `file_path` 讀取指定的 CSV 檔案。
  - 為了提高彈性，它會嘗試將常見的中文欄位名 (如 `時間`, `開盤價`) 對應到標準的英文欄位名 (`Datetime`, `Open`)。
- **寫入資料庫**:
  - 使用 Pandas 讀取 CSV 檔案後，透過 `to_sql` 方法並設定 `if_exists='append'` 和 `index=False`，將標準化後的 DataFrame 高效地寫入 `market_data` 資料表中。
  - 資料庫的 `PRIMARY KEY` 約束會自動處理重複資料的過濾。

### 4.4 前端整合 (`App.vue`)
- **新增按鈕與互動流程**:
  1. 在 `index.html` 的操作區塊，新增一個「匯入K棒資料」按鈕。
  2. 點擊按鈕觸發 `showKDataModal` 函式。
- **檔案選擇彈窗**:
  1. `showKDataModal` 首先呼叫 `/api/kdata_files` API，獲取檔案列表。
  2. 獲取成功後，將檔案列表顯示在一個彈出視窗(Modal)中，讓使用者選擇。
- **觸發匯入 API**:
  1. 使用者從列表中選擇一個檔案並點擊「確認匯入」。
  2. 前端觸發 `importKData` 函式，該函式會向後端的 `/api/import_kdata` 端點發送一個 `POST` 請求，並在請求主體中附上使用者選擇的檔名。
  3. 請求成功後，會使用 `alert` 彈窗向使用者顯示後端回傳的匯入結果訊息。

---

## 6. K線圖除錯歷程 (K-Line Chart Debugging Journey)

在整合 K 線圖功能後，遇到了「圖表無法正常顯示」的問題。此問題的除錯過程較為曲折，涉及了前端渲染、資料載入及 API 呼叫等多個層面，最終發現是由三個獨立但環環相扣的 Bug 所引起。

### 6.1 Bug 1：圖表渲染失敗

- **現象**: 前端畫面中，應顯示圖表的位置完全空白，沒有任何反應。
- **分析**:
    1.  首先檢查 `KlineChart.vue` 元件，確認其 `lightweight-charts` 函式庫的初始化邏輯。
    2.  發現成交量圖層 (Histogram Series) 的設定中，使用了一個可疑的屬性：`priceScaleId: ''`。
    3.  查閱 `lightweight-charts` 官方文件，確認此寫法不正確或已過時，其意圖是想將成交量圖層疊加在主圖表窗格上。錯誤的 ID 可能導致函式庫內部拋出未被捕獲的錯誤，中斷渲染流程。
- **解決方案**:
    將不正確的 `priceScaleId: ''` 修改為 `pane: 0`。`pane: 0` 是當前官方推薦的標準寫法，能明確地將圖層指定到第 0 個窗格（主圖表窗格），從而解決了渲染失敗的問題。

### 6.2 Bug 2：圖表顯示「找不到資料」

- **現象**: 解決了渲染 Bug 後，圖表元件成功載入，但顯示「資料庫中找不到K線資料，請先匯入K線圖檔案」的提示訊息。
- **分析**:
    1.  此訊息表示前端成功呼叫了後端 API (`/api/kline_data`)，但 API 回傳了一個空陣列。
    2.  檢查後端 `server.py`，確認 API 只有在資料庫 `market_data` 表為空時，才會回傳空陣列。
    3.  檢查 `KData/` 目錄，確認 `.csv` 原始檔案存在且內容格式正確。
    4.  懷疑是「資料匯入」環節出了問題。為了驗證，修改 `server.py`，使其在啟動時自動執行資料匯入腳本 `import_kdata.py`。
    5.  為了進一步追蹤，修改 `import_kdata.py`，加入詳細的偵錯日誌，以印出它實際找到的檔案和匯入的筆數。
- **根本原因定位**:
    重啟伺服器後，從使用者回饋的後端日誌中發現關鍵訊息：`New records: 0, Skipped duplicates: 23960.`。這表示**資料早就存在於資料庫中**，每次匯入都因主鍵重複而被略過。因此，「找不到資料」的真正原因並非未匯入，而是 API 查詢結果為空，這是一個新的矛盾。

### 6.3 Bug 3：API 呼叫靜默失敗

- **現象**: 承上，既然資料在庫中，為何 API 查詢結果為空？為了驗證，在 API 函式 (`get_kline_data`) 內部加入日誌，計算 `market_data` 表的總筆數。然而，在請使用者點擊前端「行情圖表」分頁後，後端**完全沒有出現**任何新的日誌，包括 API 被呼叫的紀錄。
- **分析**:
    這表示問題的根源再次反轉：**前端在點擊分頁時，根本沒有成功向後端發出 API 請求**。
- **根本原因定位**:
    1.  重新檢查 `App.vue`（主元件）和 `KlineChart.vue`（圖表元件）。
    2.  發現 `App.vue` 中的所有 API 呼叫都使用了 `http://localhost:8000` 作為基底 URL。
    3.  然而 `KlineChart.vue` 中的 API 呼叫卻是寫死的相對路徑：`fetch('/api/kline_data')`。
    4.  由於前端開發伺服器運行在 `http://localhost:5173`，此相對路徑請求會發往 `http://localhost:5173/api/kline_data`，這是一個錯誤的、不存在的位址。請求在瀏覽器端就已失敗，因此後端伺服器（運行在 `8000` 埠）自然不會收到任何請求。
- **解決方案**:
    修改 `KlineChart.vue`，為其 `fetch` 呼叫加上 `http://localhost:8000` 的前綴，使其指向正確的後端 API 位址。

### 結論
K 線圖無法顯示的問題，是由**圖表渲染選項錯誤**、**資料導入流程誤解**、**前端 API 位址寫死錯誤**三個獨立問題串連疊加導致的。透過逐層分析、添加日誌、正反驗證，最終定位並解決了所有問題。

---

## 7. K線圖工具列功能規格 (Specification for K-Line Chart Toolbar)

此章節記錄了為 K 線圖增加進階分析工具列的設計規格。

### 7.1 整體設計 (Overall Design)

- **位置**: 在「行情圖表」分頁的 K 線圖正上方，新增一個水平的工具列區域。
- **風格**: 工具列將採用簡潔、現代的設計，按鈕和下拉選單會清晰地分組，與現有 UI 風格保持一致。

### 7.2 功能規格 (Functional Specifications)

1.  **時間週期切換 (Timeframe Selection)**
    - **功能描述**: 提供一個下拉選單，讓使用者可以切換不同的 K 線時間週期。
    - **選項**:
        - 1 分鐘 (1m) - (預設)
        - 5 分鐘 (5m)
        - 15 分鐘 (15m)
        - 1 小時 (1h)
        - 日線 (1D)
    - **實作方式**:
        - **後端 (`server.py`)**: `/api/kline_data` 端點將會新增一個 `timeframe` 參數。當收到請求時，後端會使用 Pandas 的 `resample()` 功能，將原始的 1 分鐘資料動態聚合成使用者請求的時間週期資料。
        - **前端 (`KlineChart.vue`)**: 當使用者從下拉選單選擇新的時間週期時，前端會帶上新參數，重新向後端請求資料並刷新圖表。

2.  **技術指標 (Technical Indicators)**
    - **功能描述**: 提供一個下拉選單或一組開關按鈕，讓使用者可以在圖表上疊加常用的技術指標。
    - **初步選項**:
        - **移動平均線 (Moving Average - MA)**: 提供 MA5, MA10, MA20, MA60 四個常用週期的開關。
        - **布林通道 (Bollinger Bands - BBands)**: 提供一個開關，用以顯示上、中、下三條軌道線 (20週期, 2個標準差)。
    - **實作方式**:
        - **前端 (`KlineChart.vue`)**: 指標的計算將在前端完成。當使用者啟用一個指標時，前端會根據現有的 K 線資料即時計算出指標數據，並使用 `lightweight-charts` 的 `addLineSeries` 功能將其繪製到圖表上。

3.  **圖表類型 (Chart Type)**
    - **功能描述**: 提供一組按鈕，讓使用者可以切換主圖的顯示類型。
    - **選項**:
        - K 線圖 (Candlestick) - (預設)
        - 線圖 (Line) - (僅收盤價連線)
    - **實作方式**:
        - **前端 (`KlineChart.vue`)**: 點擊按鈕時，會移除當前的圖表序列，並使用相同的資料重新建立一個不同類型的圖表序列。

4.  **匯出圖表 (Export Chart)**
    - **功能描述**: 提供一個「下載圖表」按鈕，讓使用者可以將當前看到的圖表畫面儲存為一張 `.png` 圖片。
    - **實作方式**:
        - **前端 (`KlineChart.vue`)**: 利用 `lightweight-charts` 內建的 `takeScreenshot()` API 來獲取圖表的 Canvas 物件，然後觸發瀏覽器下載該圖片。

---

## 8. K線圖頁面縮放與資料適配規格 (K-Line Chart Zoom & Data Fit Specification)

### 8.1 資料適配與自動縮放 (Data Fit & Auto-Zoom)
- **功能描述**: K線圖在初始化或數據更新後，應自動調整其時間軸與價格軸（Y軸）縮放級別，以確保所有可視數據點都能完整顯示在圖表區域內，K棒能正常顯示且不縮成一條線，並且Y軸能隨著資料的高低點自動適配。當瀏覽器窗口大小改變時，圖表應自適應調整大小並重新適配數據。
- **實作方式**:
    - 利用 `lightweight-charts` 提供的 `chart.timeScale().fitContent()` 方法，在圖表初始化及數據更新時呼叫，以實現內容的自動適配。這將確保時間軸和價格軸都自動調整以包含所有可見數據。
    - 利用 `window.addEventListener('resize', resizeHandler)` 監聽窗口大小變化事件，並在 `resizeHandler` 中調用 `chart.resize()` 和 `chart.timeScale().fitContent()`。
- **驗證狀態**: 已驗證 K棒畫面縮放與資料適配功能正常，K棒顯示正常大小，Y軸隨資料變動自動適配。

### 8.2 手動縮放功能 (Manual Zoom Functionality)
- **功能描述**: 提供用戶界面元素，讓用戶可以手動控制圖表的縮放級別。
- **初步選項**:
    - **縮放按鈕**: 提供「放大」和「縮小」按鈕。
    - **重置縮放按鈕**: 提供一個按鈕，將圖表縮放級別重置為自動適配所有數據的初始狀態。
- **實作方式**:
    - **前端 (`KlineChart.vue`)**:
        - 在工具列中新增「放大」、「縮小」及「重置縮放」按鈕。
        - 利用 `lightweight-charts` API 提供的時間軸方法來控制縮放：
            - `chart.timeScale().scrollPosition()` 可以獲取或設置當前滾動位置。
            - `chart.timeScale().setVisibleRange()` 可以設定可視範圍。
            - 手動縮放功能可能需要計算當前可視K棒的數量，並根據比例調整 `setVisibleRange`。
            - `chart.timeScale().fitContent()` 用於重置縮放。

### 8.3 Y軸範圍手動設定 (Manual Y-axis Range Setting)
- **功能描述**: 允許使用者手動設定 K 線圖 Y 軸的最大值與最小值，以便更精確地觀察特定價格區間。
- **初步選項**:
    - **輸入欄位**: 提供兩個輸入欄位，分別用於設定 Y 軸的最大值和最小值。
    - **應用按鈕**: 一個按鈕用於應用手動設定的範圍。
    - **重置按鈕**: 一個按鈕用於將 Y 軸範圍重置為自動適配模式。
- **實作方式**:
    - **前端 (`KlineChart.vue`)**:
        - 在工具列中新增輸入欄位和按鈕。
        - 利用 `lightweight-charts` API 提供的 `chart.priceScale('right').applyOptions({ mode: 'normal', autoscaleInfoProvider: undefined, visible: true, scaleMargins: { top: 0.1, bottom: 0.25 } })` 或 `chart.priceScale('right').setVisibleRange({ from: minValue, to: maxValue })` 來設定 Y 軸的可視範圍。
        - 當使用者輸入值並點擊應用時，呼叫上述 API 進行設定。
        - 重置時，呼叫 `chart.timeScale().fitContent()`，`lightweight-charts` 會自動計算 Y 軸範圍。

---

## 9. 圖層管理功能規格 (Layer Management Feature Specification)

### 9.1 功能描述
提供用戶在K線圖上疊加顯示不同資料系列或視覺元素的能力，例如交易訊號、指標線、事件標記等。每個圖層應可獨立開啟/關閉顯示、調整樣式或設定。

### 9.2 初步選項
*   **預設圖層**: K線圖本身作為基礎圖層。
*   **可選圖層類型**:
    *   **交易資料圖層 (Trade Data Layer)**: 在 K 線圖上顯示買入/賣出交易點，以特定圖示（例如：箭頭）標示。
    *   **移動平均線 (MA)**: 不同週期的移動平均線 (MA)。
    *   **成交量 (Volume)**: 底部成交量圖。
    *   **布林通道 (Bollinger Bands)**: 布林通道的上下軌和中軌。
    *   **自訂指標 (Custom Indicators)**: (未來可擴充其他技術指標，例如 RSI, MACD 等)。
    *   **事件標記 (Event Markers)**: (未來可擴充特定日期或時間點的文字/圖示標記)。

### 9.3 用戶界面 (UI) 設計
*   **圖層控制面板**: 在圖表上方或側邊增加一個可展開/收合的面板，列出所有可用的圖層。
*   **圖層開關**: 每個圖層旁應有勾選框或開關按鈕，控制其顯示與隱藏。
*   **圖層設定**: 每個圖層旁可提供一個齒輪圖示或下拉選單，用於調整該圖層的樣式 (例如：線條顏色、粗細、標記圖示) 或參數 (例如：均線週期)。

### 9.4 實作方式

#### 前端 (`KlineChart.vue` 及相關組件)
1.  **資料結構定義**:
    *   定義圖層的資料結構，包含 `id`, `name`, `type`, `isVisible`, `settings` (例如: `color`, `period` 等)。
2.  **圖層狀態管理**:
    *   在 `KlineChart.vue` 或 Vuex (如果專案有使用) 中管理活躍圖層的狀態。
    *   狀態應包含哪些圖層被啟用，以及它們各自的設定。
3.  **UI 組件開發**:
    *   創建一個新的 Vue 組件 `LayerControl.vue` (或類似名稱)，用於顯示圖層列表和控制選項。
    *   `LayerControl.vue` 將透過 props 接收可用的圖層定義，並透過 emit 事件通知父組件 `KlineChart.vue` 圖層狀態的改變。
4.  **`lightweight-charts` API 整合**:
    *   `KlineChart.vue` 將根據 `LayerControl.vue` 傳來的狀態，動態地使用 `lightweight-charts` API 創建、更新或移除圖層。
    *   **基礎K線圖**: 作為主系列 (main series)，不可關閉。
    *   **疊加系列 (Overlay Series)**:
        *   對於均線、交易訊號等，需要創建新的 `series` (例如 `chart.addLineSeries()`, `chart.addHistogramSeries()` 等)。
        *   根據圖層設定，動態配置系列屬性 (例如顏色、線寬)。
        *   交易訊號可能需要使用 `chart.timeScale().createPriceLine()` 或 `series.setMarkers()` 來添加標記。
    *   **資料載入**: 確保不同圖層所需的資料 (例如均線計算結果、交易訊號資料) 能被正確地載入並傳遞給 `lightweight-charts`。
5.  **樣式和互動**:
    *   確保圖層控制面板的樣式與現有界面一致。
    *   處理圖層開關和設定變更時的即時圖表更新。

#### 後端 (如果圖層資料需要後端計算或提供)
*   **API 接口**: 如果某些圖層 (例如複雜指標) 的資料需要在後端計算，則需要定義新的 API 接口供前端調用。
*   **資料處理**: 後端負責接收前端請求，計算所需指標資料，並以標準格式返回給前端。