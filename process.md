# TradeCheck 系統實作與設計決策
- **版本**: v2.6
- **最後更新日期**: 2025-12-11

本文檔旨在記錄 `TradeCheck` 專案在根據 `spec.md` 進行功能開發時，其核心功能的實作摘要、關鍵的設計決策與問題修正過程。它並非鉅細靡遺的步驟紀錄，而是為了幫助未來的維護者快速理解系統的設計思路與重要權衡。

---

## 功能擴充與實作 (v2.6)

在 `v2.6` 版本中，我們為系統新增了兩項關鍵功能，以提升資料管理的靈活性。

### 1. 擴充交易資料匯入功能 (Expanding Trade Data Import)

為了進行更全面的交易分析，我們擴充了原有的交易資料匯入功能，使其能夠處理來源 CSV 檔案中的所有欄位。

- **需求**: 原系統只匯入 `成交時間`, `買賣別`, `商品名稱`, `口數`, `平倉損益淨額` 五個欄位。新需求希望能將 `新倉價`, `平倉價`, `手續費`, `期交稅` 等所有欄位一併匯入。
- **後端修改 (`trade_check.py` & `server.py`)**:
    1.  **資料庫結構更新**: 修改 `server.py` 中的 `init_database` 函式，在 `trades` 資料表的 `CREATE TABLE` 語句中新增了 `open_price REAL`, `close_price REAL`, `fee REAL`, `tax REAL` 四個欄位。
    2.  **資料處理邏輯更新**: `trade_check.py` 中的 `load_transactions_from_csv` 方法被更新，其欄位對應字典 `column_mapping` 已擴充，納入了所有新欄位，並進行了對應的型別轉換。
    3.  **匯入邏輯更新**: 修改 `server.py` 中的 `import_trades_from_file` 函式，將其 `INSERT OR IGNORE` SQL 語句擴充，使其能夠接收並寫入所有新欄位的資料。
- **結果**: 現在，當使用者透過 `/api/import_trades` 端點匯入 `tradedata` 的 CSV 檔案時，所有欄位都會被完整地存入資料庫，為未來的詳細分析奠定了基礎。

### 2. 新增清空交易資料功能 (Adding Clear Trades Data Feature)

為了方便使用者重新開始或清除測試資料，系統新增了清空所有交易紀錄的功能。

- **後端實作 (`server.py`)**:
    1.  **新增 API 端點**: 建立了一個新的 `POST /api/clear_trades` 端點。使用 `POST` 而非 `GET` 是因為此操作會修改伺服器狀態，屬於非冪等操作。
    2.  **核心邏輯**: 該端點的函式會連接到 `trade_notes.db` 資料庫，並對 `trades` 資料表執行 `DELETE FROM trades` SQL 指令。
    3.  **日誌與回饋**: 為了確保操作可追蹤，該函式會在執行前後記錄警告級別的日誌。為提供準確的回饋，它會先查詢刪除前的總筆數，再執行刪除，最後回傳一個包含已刪除筆數的成功訊息給前端。

- **前端實作 (`frontend/src/App.vue`)**:
    1.  **新增 UI 元件**: 在左側的控制面板中，新增了一個紅底白字的「清空交易資料」按鈕 (`clear-button`)，其醒目的樣式旨在提醒使用者這是一個具破壞性的操作。
    2.  **實作確認流程**:
        -   點擊按鈕時，會觸發 `clearAllTrades` 方法。
        -   該方法首先會呼叫瀏覽器原生的 `window.confirm()` 函式，彈出一個模式對話框，再次詢問使用者「您確定要清空所有交易資料嗎？此操作無法復原。」
    3.  **觸發 API 呼叫**:
        -   只有當使用者點擊「確認」後，程式才會繼續執行，使用 `fetch` API 向後端的 `/api/clear_trades` 端點發送 `POST` 請求。
        -   若使用者取消操作，則只在日誌中記錄，不執行任何動作。
    4.  **結果處理**:
        -   API 呼叫成功後，使用 `window.alert()` 顯示後端回傳的成功訊息 (例如「成功清空 XXX 筆交易資料」)。
        -   之後，立即呼叫 `window.location.reload()` 來重新整理整個應用程式，確保圖表和報告都反映出資料已被清空的最新狀態。
---
(The rest of the file remains as it was)
...
---
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

### 2.7 錯誤七：交易資料圖層顯示異常 - `TypeError: Cannot read properties of undefined (reading 'toLowerCase')` (已解決)

- **錯誤現象**: 當前端 K 線圖啟用「交易資料圖層」後，交易資料（買賣點箭頭）無法正常顯示在圖表上。瀏覽器控制台顯示 `TypeError: Cannot read properties of undefined (reading 'toLowerCase') at KlineChart.vue:437:30`。
- **根本原因分析**:
    - 此錯誤發生在 `frontend/src/KlineChart.vue` 的 `drawTradeData` 函式中，當程式嘗試將從後端獲取的交易資料映射為 `lightweight-charts` 所需的 `marker` 格式時。
    - 錯誤訊息表明程式試圖在一個 `undefined` 的值上呼叫 `toLowerCase()` 方法。經排查，原因是從後端 `/api/trade_data` 傳來的某些交易資料物件，缺少 `action` 屬性，或該屬性的值為 `null`。
- **解決方案**:
    - **前端防禦性程式設計**: 在 `KlineChart.vue` 的 `drawTradeData` 函式中，對 `tradeData` 陣列進行 `map` 操作時，加入了對 `trade.action` 屬性的存在性檢查。在呼叫 `.toLowerCase()` 之前，確保該屬性為一個有效的字串，若不存在則給予預設值。
      ```javascript
      // 示例修正
      const markers = tradeData.value.map(trade => {
        const action = trade.action || ''; // 提供預設值，防止 undefined 錯誤
        return {
          time: trade.time,
          position: action.toLowerCase() === 'buy' ? 'belowBar' : 'aboveBar',
          color: action.toLowerCase() === 'buy' ? '#26A69A' : '#EF5350',
          shape: action.toLowerCase() === 'buy' ? 'arrowUp' : 'arrowDown',
          text: `Trade @ ${trade.price}`
        };
      }).filter(marker => marker.time); // 過濾掉無效數據
      ```
    - **後端資料校驗 (建議)**: 同時建議在後端 `/api/trade_data` API 的輸出端進行更嚴格的資料清理，確保所有回傳給前端的交易物件都包含完整的必要欄位。
- **狀態**: **已解決**。前端加上防禦性檢查後，即使後端傳來不完整的資料，圖表也能正常渲染，不會再因單筆資料問題而崩潰。交易標記已可成功顯示。

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

## 10. K線圖功能穩定性修復歷程 (v2.4)

在 `v2.4` 版本中，針對 K 線圖功能進行了一系列的穩定性修復，解決了從後端資料處理到前端渲染的多個潛在問題。

### 10.1 問題一：伺服器啟動失敗 (`NameError`)
- **現象**: 應用程式在啟動時直接崩潰，日誌顯示 `NameError: name 'init_database' is not defined`。
- **根本原因**: 在先前的程式碼修改過程中，用於初始化資料庫的 `init_database` 函式被意外地刪除或移動，導致 FastAPI 的啟動事件 (`startup_event`) 找不到該函式。
- **解決方案**: 重新將 `init_database` 函式及其 `@app.on_event("startup")` 掛鉤的完整程式碼區塊添加回 `server.py` 的頂層範圍，並確保其位置穩固，不易被後續修改影響，從根本上解決了啟動失敗的問題。

### 10.2 問題二：切換時間週期後圖表消失
此問題的根源較為複雜，由後端資料處理邏輯與前端渲染邏輯的雙重錯誤導致。

#### a. 後端資料處理錯誤
- **現象**: 當使用者從預設的 `1T` 切換到 `5T` 或 `1H` 等較大的時間週期時，圖表消失，並顯示「沒有資料」。
- **分析歷程**:
    1.  **初步假設**: 以為是後端回傳了空陣列 `[]`。
    2.  **增加日誌**: 在 `server.py` 的 `get_kline_data` 函式中加入詳細的日誌，追蹤資料在每個處理步驟後的筆數。
    3.  **關鍵發現**: 日誌顯示，即使在切換時間週期後，後端依然處理了數萬筆資料 (`Final chart_data has 36595 records`)，**推翻了「後端回傳空陣列」的假設**。問題點必定在前端。
- **後端邏輯優化 (即便非問題主因)**:
    - 儘管後端並非導致問題的主因，但在此過程中也對其資料處理邏輯進行了優化。
    - **舊邏輯**: `resample(...).dropna()`。這個 `dropna()` 過於嚴格，會移除任何包含 `NaN` 的資料列，容易在資料不足時產生空結果。
    - **新邏輯**: `resample(...).dropna(subset=['open', 'high', 'low', 'close'], how='all')`，然後再對整個 DataFrame 進行 `.replace({np.nan: None})`。這個作法更為強健，它只移除那些連 OHLC 核心資料都湊不齊的無效 K 棒，並將剩餘的零星 `NaN` 值（例如 `volume`）替換為 JSON 相容的 `null`，避免了潛在的序列化錯誤。

#### b. 前端渲染錯誤 (真正原因)
- **現象**: 既然後端回傳了 36,595 筆有效資料，為何前端仍顯示空白？
- **分析**: 唯一的可能性是前端在收到新資料後，執行渲染的過程中發生了 JavaScript 錯誤，導致後續的繪圖程式碼被中斷。
- **根本原因定位**:
    1.  重新審閱 `KlineChart.vue` 中的 `setupChart` 函式。
    2.  發現其更新邏輯是「先銷毀舊圖表，再建立新圖表」。
    3.  錯誤點在於：程式碼在 `chart.remove()` (銷毀舊圖表) **之後**，還試圖呼叫 `chart.removeSeries(candlestickSeries)`。此時，`chart` 變數已指向一個**全新的、空白的圖表實例**，而 `candlestickSeries` 變數仍然是**屬於舊圖表的序列**。試圖從新圖表中移除一個不屬於它的序列，會導致 `lightweight-charts` 內部拋出錯誤。
- **解決方案**:
    - 修改 `setupChart` 的邏輯。在 `chart.remove()` 執行後，代表舊圖表及其所有子序列都已被一併銷毀。
    - 因此，只需將所有序列變數 (如 `candlestickSeries`, `volumeSeries` 等) 手動設為 `null`，以表示它們已失效即可。**移除所有多餘且錯誤的 `chart.removeSeries(...)` 呼叫**。
    - 這個修正理順了圖表的銷毀與重建流程，確保了在收到新時間週期的資料後，圖表能夠被乾淨且正確地重新繪製。

### 10.3 結論
K 線圖時間週期切換失敗的問題，是由後端一個不夠強健的資料處理邏輯，和前端一個致命的圖表更新邏輯錯誤共同導致的。在釐清後端正常回傳資料後，最終將問題定位在前端的渲染腳本上，並透過修正圖表重建流程而獲得解決。
---

## 11. K線圖 Y 軸縮放異常之根本原因與最終解決方案 (v2.5)

在 `v2.5` 版本中，系統解決了一個長期存在的 K 線圖 Y 軸縮放異常問題。

### 11.1 問題現象
- 當在 K 線圖上啟用技術指標（如移動平均線 MA、布林通道 BBands）時，圖表的 Y 軸會被異常拉伸，導致主要的 K 線圖被壓縮成一條幾乎無法辨識的水平線。
- 這個問題是一個「回歸 (Regression)」問題，它在一次為了修正「指標或交易圖層無法顯示」的修改後出現。

### 11.2 根本原因分析
經過詳細的偵錯，根本原因被定位在 `lightweight-charts` 函式庫的預設縮放行為上：

1.  **預設縮放範圍的限制**: `lightweight-charts` 的 `autoScale` 功能，在預設情況下，只會根據主要的價格序列 (Candlestick Series) 的最高價與最低價來決定 Y 軸的縮放範圍。
2.  **指標線超出範圍**: 當指標線（例如，一條高於所有 K 棒最高價的 MA 線）的數值超出了 K 棒本身的價格區間時，預設的 `autoScale` 不會將其納入計算，導致指標線被「切掉」而無法顯示。
3.  **不完美的歷史修正**: 為了解決上述「指標線被切掉」的問題，過去的某次修改可能採用了一個不完美的方案（例如，錯誤地將成交量序列綁定到價格軸上），雖然強迫顯示了指標，但卻污染了價格軸的縮放計算，引發了更嚴重的「Y 軸被異常拉伸」的問題。

最終的結論是：一個穩健的解決方案，必須能**強制 Y 軸的自動縮放範圍，動態地包含 K 線本身以及所有可見的指標線**。

### 11.3 最終解決方案
為了一次性地、徹底地解決這個「按下葫蘆浮起瓢」的兩難問題，我們採用了以下幾個關鍵的實作：

1.  **實作 `autoscaleInfoProvider`**:
    - 這是本次修正的核心。我們在 `createChart` 的 `priceScale` 選項中，提供了一個自訂的 `autoscaleInfoProvider` 回呼函式。
    - **運作原理**: 這個函式會在每次圖表需要重新計算 Y 軸範圍時（例如，平移、縮放、或指標變更時）被呼叫。在函式內部，它會：
        a. 獲取當前圖表的可見時間範圍。
        b. 遍歷這個範圍內**所有可見的數據**，包括主要的 K 線數據，以及所有被啟用的指標線數據 (MA, BBands)。
        c. 手動找出這些數據中的絕對最高價 (`maxValue`) 與最低價 (`minValue`)。
        d. 將這個計算出的 `{ minValue, maxValue }` 物件回傳給圖表。
    - **效果**: 透過這個機制，我們等於是手動接管並擴展了 `autoScale` 的能力，使其能夠完美地將所有圖層都納入縮放考量，確保沒有任何圖線會被切掉，同時 K 線圖也能維持正確的比例。

2.  **確保成交量圖獨立**:
    - 再次確認 `volumeSeries` (成交量圖) 的設定是完全獨立的。最終採用 `priceScaleId: 'volume_scale'` 給予其一個獨立的價格軸 ID (或完全不設定，使其自動產生新窗格)，確保它擁有自己獨立的 Y 軸，不與主價格圖衝突。

3.  **強化數據清洗**:
    - 作為一個防禦性措施，在 `fetchData` 函式中增加了一道過濾器，可以在收到後端數據時，就自動移除任何價格為 `0` 或無效的 K 線數據，增加了圖表整體的穩定性。

透過以上「`autoscaleInfoProvider` + 獨立成交量圖 + 數據清洗」的組合，徹底解決了長久以來的 Y 軸縮放問題，並讓圖表功能在各種使用情境下都更加穩健可靠。
---

## 交易資料顯示優化 (Trade Data Display Enhancement)

為了在K線圖上提供更豐富的交易資訊，將對交易圖層進行功能優化。

### 1. 後端 (server.py)

- **目標**:
  - 確認後端 API (`/api/trade_data`) 回傳的交易資料包含所有必要的欄位。
- **實作**:
  - 交易資料匯入流程 (`/api/import_trades`) 將進行修改，以處理包含 `新倉價 (open_price)` 和 `平倉價 (close_price)` 的CSV檔案。這些欄位將與 `成交時間 (trade_time)`, `口數 (contracts)`, 和 `平倉損益淨額 (net_pnl)` 一同存入 `trades` 資料庫。
  - `GET /api/trade_data` 函式將被修改，其 SQL 查詢及回傳的 JSON 物件會確保包含 `trade_time`, `contracts`, `open_price`, `close_price`, 以及 `net_pnl`。

### 2. 前端 (KlineChart.vue)

- **目標**:
  - 在 K 線圖上繪製交易標記，並在用戶滑鼠懸停時顯示包含詳細資訊的提示框 (Tooltip)。
- **實作**:
  - **修改 `drawTradeData` 函式**:
    - 將修改此函式，為每個交易標記附加一個自定義的提示框。
  - **設計提示框內容**:
    - 提示框將顯示一個列表或表格，包含：`成交時間`, `口數`, `新倉價`, `平倉價`, `平倉損益淨額`。
  - **實現條件性顏色**:
    - 在提示框的 `平倉損益淨額` 欄位上，將使用 Vue.js 的綁定語法來動態設定 CSS class。
    - 如果 `平倉損益淨額 > 0`，文字顏色設為藍色。
    - 如果 `平倉損益淨額 < 0`，文字顏色設為紅色。
  - **更新圖表**:
    - 確保在獲取新數據或切換可見性時，圖表能正確地重繪或清除這些交易標記及其提示框。

### 3. 測試與驗收

- **目標**:
  - 確保新功能如預期般運作。
- **步驟**:
  1. 啟動應用程式。
  2. 在圖表上啟用「交易資料」圖層。
  3. 滑鼠移動到圖表上的交易標記上。
  4. **驗證**:
      - 是否彈出包含所有指定欄位的提示框？
      - `平倉損益淨額` 的顏色是否根據其正負值正確顯示（正為藍，負為紅）？
      - 資料內容是否正確？

---

## 後端錯誤修復與交易圖層功能恢復

在擴充交易資料欄位後，交易圖層及除錯資訊完全消失。本節記錄了對此問題的診斷與修復過程。

### 1. 問題現象

- **前端**: K線圖上的「交易資料」圖層及其開關、除錯資訊面板均未顯示。
- **後端**: 伺服器日誌顯示 `500 Internal Server Error`，並伴隨著兩類關鍵錯誤。

### 2. 根本原因分析

#### a. 後端資料庫錯誤 (`sqlite3.OperationalError`)
- **錯誤日誌**: `pandas.errors.DatabaseError: Execution failed on sql ...: no such column: t.open_price`。
- **原因**: 這是問題的核心。在先前「交易資料顯示優化」的需求中，後端 `server.py` 的 `/api/trade_data` 端點被修改，使其在 SQL 查詢中加入了 `t.open_price` 和 `t.close_price` 欄位。然而，對應的 `trades` 資料庫表結構並未同步更新，亦未修改資料匯入流程來寫入這兩個欄位。因此，當 API 執行此查詢時，資料庫因找不到欄位而拋出嚴重錯誤。
- **連帶影響**: 前端呼叫 `/api/trade_data` 時收到 500 錯誤，導致其無法獲取交易資料，進而觸發了「隱藏交易圖層及相關UI」的錯誤處理邏輯。

#### b. 後端啟動錯誤 (`NameError`)
- **錯誤日誌**: `NameError: name 'app' is not defined`，發生在 `@app.on_event("startup")` 裝飾器。
- **原因**: 這是一個獨立但同樣致命的啟動問題。此錯誤表示在 `server.py` 中，FastAPI 的應用實例 `app` 在被 `@app` 裝飾器使用時還尚未被定義。通常這是因為 `app = FastAPI()` 這行程式碼被誤刪，或被移動到了裝飾器定義的下方，違反了 Python 的執行順序。

### 3. 修復過程

1.  **修復後端啟動錯誤**:
    - **操作**: 檢查 `server.py`，將 `app = FastAPI()` 這行程式碼移至檔案頂部區域，確保它在任何 `@app` 裝飾器被定義之前執行。
    - **結果**: 伺服器恢復了正常啟動能力。

2.  **修復後端資料庫查詢錯誤 (緊急措施)**:
    - **操作**: 為了立即恢復前端功能，暫時性地修改 `server.py` 中的 `get_trade_data` 函式，將 SQL 查詢中的 `t.open_price` 和 `t.close_price` 兩個欄位移除。
    - **結果**: `/api/trade_data` 端點不再拋出資料庫錯誤，能夠成功回傳基礎的交易資料。

3.  **驗證前端恢復**:
    - **操作**: 重啟前後端應用。
    - **結果**: 由於後端 API 已能正確回應，前端成功獲取資料，K線圖上的「交易資料」圖層、開關及除錯資訊面板均已恢復正常顯示。

### 4. 後續計畫

本次修復恢復了系統的可用性，但「顯示新倉/平倉價」的功能尚未完成。下一步將進行完整的實作：

1.  **更新資料庫結構**: 修改 `init_database` 函式，在 `trades` 表的 `CREATE TABLE` 語句中加入 `open_price REAL` 和 `close_price REAL` 欄位。
2.  **更新資料匯入流程**: 修改 `/api/import_trades` 及其相關的資料處理邏輯，使其能夠從來源 CSV 檔案中讀取 `新倉價` 和 `平倉價`，並將其寫入資料庫的新欄位中。
3.  **還原 API 查詢**: 在完成前兩步後，將 `t.open_price` 和 `t.close_price` 重新加入到 `get_trade_data` 的 SQL 查詢中。
4.  **完成前端功能**: 確保前端 `KlineChart.vue` 能正確接收並在提示框中顯示這些新欄位。