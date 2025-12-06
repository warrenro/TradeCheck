# TradeCheck 系統實作與設計決策
- **版本**: v1.5
- **最後更新日期**: 2025-12-06

本文檔旨在記錄 `TradeCheck` 專案在根據 `spec.md` 進行功能開發時，其核心功能的實作摘要、關鍵的設計決策與問題修正過程。它並非鉅細靡遺的步驟紀錄，而是為了幫助未來的維護者快速理解系統的設計思路與重要權衡。

---

## 1. 核心功能實作摘要 (Core Feature Implementation Summary)

為了實現 `spec.md` 中定義的複雜分析與審計功能，`trade_check.py` 腳本的核心邏輯被組織成一系列獨立的函式，並由主函式 `run_audit` 進行統籌調用。以下是關鍵模組的職責劃分：

- **`config.ini` 整合**:
  - 程式啟動時會讀取 `config.ini`，獲取 `目前權益數`、`月初本金`、`操作規模` 等使用者自定義參數，實現了設定與程式碼的分離。

- **`load_transactions` (資料讀取)**:
  - 負責讀取 `tradedata/` 目錄下的交易紀錄，並驗證 `成交時間`, `買賣別`, `平倉損益淨額`, `口數`, `商品名稱` 等必要欄位是否存在。

- **`_add_trade_points_column` (計算交易點數)**:
  - 根據 `商品名稱` 決定點值 (50/10/200)，計算每筆交易的「點數」 (`points`)，作為交易 DNA 診斷的基礎。

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

### 2.5 錯誤四：前端畫面無法顯示審計報告

- **錯誤現象**: 前端成功呼叫 API 並取得數據後，畫面並未渲染出審計報告，而是停留在初始狀態。
- **根本原因**: `TradeCheck/frontend/src/App.vue` 檔案中，月度總結表格的資料綁定路徑有誤。程式碼嘗試存取 `summary.incentive.amount` 來顯示激勵獎金，但根據後端 API 回傳的資料結構，正確的路徑應為 `summary.happiness_incentive.amount`。這個錯誤的路徑導致 Vue 在渲染時拋出執行階段錯誤，中斷了畫面的更新。
- **解決方案**:
    1.  **定位問題**: 檢查瀏覽器開發者主控台，發現 Vue 的渲染錯誤，指向 `App.vue` 範本中的一個屬性存取問題。
    2.  **修正路徑**: 將範本中的 `formatCurrency(summary.incentive.amount)` 修改為 `formatCurrency(summary.happiness_incentive.amount)`，使其與 `historical_summary` 物件的資料結構保持一致。
    ```vue
    <!-- 錯誤的程式碼 -->
    {{ summary.happiness_incentive.eligible ? formatCurrency(summary.incentive.amount) : summary.happiness_incentive.status }}

    <!-- 修正後的程式碼 -->
    {{ summary.happiness_incentive.eligible ? formatCurrency(summary.happiness_incentive.amount) : summary.happiness_incentive.status }}
    ```
- **影響**: 此修正恢復了前端的渲染能力，確保 API 回傳的報告能夠被正確地呈現在使用者介面中。

### 2.6 錯誤五：後端資料處理與序列化錯誤

在處理特定資料檔案時，系統發生了兩類主要的後端錯誤，導致審計流程中斷。

- **錯誤現象一**: 伺服器日誌顯示 `TypeError: argument of type 'float' is not iterable`。
- **根本原因一**:
    此錯誤發生在 `_add_trade_points_column` 函式內部調用的 `calculate_points` 方法中。當交易紀錄 CSV 檔案的 `商品名稱` (`product_name`) 欄位有缺失值 (空值) 時，Pandas 會將其讀取為 `NaN` (Not a Number)，其資料型別為 `float`。後續的程式碼嘗試對這個 `float` 型別的 `product_name` 進行字串匹配迭代，從而引發 `TypeError`。
- **解決方案一**:
    在 `calculate_points` 函式中，對傳入的 `product_name` 進行型別檢查與轉換。在進行迭代匹配之前，先確保它是一個字串。如果值為 `NaN` 或其他非字串類型，則將其視為空字串，避免了迭代錯誤，並使其能夠安全地走完流程（雖然可能找不到對應的點值）。

    ```python
    # trade_check.py - calculate_points 修正
    product_name = row['product_name']
    # 確保 product_name 是字串
    if not isinstance(product_name, str):
        product_name = ""
    
    # 後續的迭代匹配...
    point_value = next((p['point'] for p in self.product_points if any(keyword in product_name for keyword in p['keywords'])), None)
    ```

- **錯誤現象二**: API 呼叫日誌顯示 `ValueError: [TypeError("'numpy.int64' object is not iterable"), TypeError('vars() argument must have __dict__ attribute')]`。
- **根本原因二**:
    此錯誤發生在 `server.py` 將審計報告回傳給前端的過程中。Pandas 在進行數據聚合時，產生的數值（如交易筆數、總損益等）其資料型別通常是 NumPy 的特定型別，例如 `numpy.int64` 或 `numpy.float64`。FastAPI 預設的 `jsonable_encoder` 無法直接將這些 NumPy 特有的數字型別序列化為標準的 JSON 格式，從而導致轉換失敗。
- **解決方案二**:
    在 `server.py` 中，將 `run_audit` 產生的報告傳遞給 `jsonable_encoder` 之前，手動將報告中的所有 NumPy 數值型別轉換為標準的 Python 型別 (如 `int`, `float`)。我實作了一個遞迴函式 `convert_numpy_types` 來遍歷整個報告字典（包括巢狀的字典和列表），並轉換所有 `numpy.integer` 和 `numpy.floating` 的實例。

    ```python
    # server.py - 新增遞迴轉換函式
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

    # 在 API 端點中呼叫
    report = auditor.run_audit(temp_file_path)
    # 在序列化前回傳前進行轉換
    json_compatible_report = convert_numpy_types(report)
    return json_compatible_report
    ```
- **影響**: 這兩項修正強化了系統的穩定性（魯棒性），使其能夠應對不乾淨的輸入資料（如缺失的商品名稱）以及處理 Python 生態系統中常見的 NumPy 資料型別，確保了 API 的正常回應與前後端資料流的順暢。經過這些修正，後端系統的核心錯誤皆已解決，應用程式現已進入穩定狀態。
