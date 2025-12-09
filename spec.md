# K-line Chart Display Specification

## 1. Overview
This document specifies the behavior and functionality of the K-line (candlestick) chart display within the TradeCheck application, focusing on data fitting, zoom capabilities, and dynamic Y-axis scaling. The chart utilizes the `lightweight-charts` library.

## 2. Core Requirements

### 2.1 Data Fitting
*   **Initial Display:** Upon loading or refreshing the K-line chart, all available historical data for the selected timeframe must be displayed, fitting entirely within the chart container's width. The chart should automatically adjust its visible range to encompass the full dataset.
*   **Responsive Resizing:** If the browser window or the chart's container size changes, the chart must automatically resize and re-fit all available data to the new dimensions.

### 2.2 Time-Scale (X-Axis) Zoom Functionality
The chart will provide both button-based and intuitive mouse-based zoom and pan functionalities for the time axis.

#### 2.2.1 Button Controls
*   **Zoom In Button:** A dedicated "Zoom In" button will allow users to magnify the chart, reducing the visible time range.
    *   Each click will reduce the visible range by a predefined factor (e.g., 20%).
    *   The zoom should center around the currently visible middle point of the chart.
    *   There is a reasonable minimum number of visible bars (e.g., 5 bars) to prevent excessive zooming into individual data points where bars might become indistinguishable.
*   **Zoom Out Button:** A dedicated "Zoom Out" button will allow users to de-magnify the chart, expanding the visible time range.
    *   Each click will increase the visible range by a predefined factor (e.g., 20%).
    *   The zoom should center around the currently visible middle point of the chart.
    *   The chart will not zoom out beyond displaying all available data.
*   **Reset Zoom Button:** A "Reset Zoom" button will instantly restore the chart to its initial state, fitting all available data within the container as described in Section 2.1.

#### 2.2.2 Mouse Interaction (Intuitive Controls)
*   **Mouse Wheel Zoom:** Users can zoom in and out of the chart using the mouse wheel.
    *   Scrolling up (away from the user) will zoom in, and scrolling down (towards the user) will zoom out.
    *   The zoom action is centered on the mouse cursor's position.
*   **Drag-to-Pan:** Users can pan (scroll horizontally) the chart by clicking and dragging with the mouse.
    *   Clicking and dragging left will move the chart view to older data.
    *   Clicking and dragging right will move the chart view to newer data.

### 2.3 Price-Scale (Y-Axis) Management
The Y-axis scaling ensures clear data visualization and provides manual control options.

*   **Automatic Data Adaptation (Auto-scaling):**
    *   When manual Y-axis range is not active, the Y-axis will automatically adjust its visible range to closely fit the high and low price points of the data currently displayed in the time-scale (X-axis) view. This ensures optimal vertical data representation, adapting dynamically as the user zooms or pans the time axis.
    *   Initial Y-axis display, and after resetting manual settings, will be auto-scaled.
*   **Manual Range Setting:**
    *   Users can manually define the minimum and maximum values for the Y-axis via dedicated input fields in the toolbar.
    *   An "Apply" button (labelled "設定Y軸範圍") will set the Y-axis to the specified minimum and maximum values, disabling automatic scaling.
    *   Validation will ensure that both inputs are valid numbers, and the maximum value is greater than the minimum.
*   **Reset Manual Range:**
    *   A "Reset" button (labelled "重設Y軸範圍") will revert the Y-axis back to its automatic scaling behavior, clearing any manually set minimum and maximum values.
*   **K-Bar Display Optimization:**
    *   To ensure K-bars are always displayed in a normal, visible size and do not collapse into thin lines, especially when zooming in, an explicit `barSpacing` is set for the `timeScale`. This helps maintain visual clarity even at higher zoom levels.

## 3. Technical Implementation Details (Internal)

*   Utilize `lightweight-charts` built-in `timeScale().fitContent()` for initial data fit and reset of X-axis zoom.
*   Leverage `lightweight-charts` `timeScale().setVisibleRange()` for programmatic X-axis zoom adjustments.
*   Configure `lightweight-charts` chart options (`handleScroll`, `handleScale`) to enable mouse wheel zoom and drag-to-pan for the X-axis.
*   `priceScale` global options within `createChart` explicitly set `autoScale: true` and `scaleMargins` for the default Y-axis behavior.
*   `priceScale().applyOptions()` on individual series (`candlestickSeries`, `lineSeries`) is used to apply manual min/max settings (`autoScale: false`, `minimum`, `maximum`) or revert to auto-scaling (`autoScale: true`, `minimum: undefined`, `maximum: undefined`).
*   `timeScale` options within `createChart` include `barSpacing` (e.g., `barSpacing: 6`) to maintain K-bar visibility.
*   Ensure `currentChartData` is consistently updated and used for all calculations.
*   Implement robust error handling and input validation for data fetching, chart rendering, and user inputs.

## 4. User Interface Considerations

*   All zoom buttons, Y-axis range input fields, and related action buttons are clearly labeled and positioned within the chart toolbar for easy access.
*   Alert messages are provided for invalid Y-axis range inputs.
*   Mouse-based interactions are standard charting behaviors, requiring no additional UI elements.

## 5. Testing
*   Verify that the chart loads with all data fitted correctly and K-bars are displayed in a normal, visible size.
*   Test "Zoom In", "Zoom Out", and "Reset Zoom" buttons for correct behavior and boundary conditions.
*   Test mouse wheel zoom (in and out) and drag-to-pan functionality.
*   Verify responsive behavior when resizing the browser window, ensuring `fitContent` and Y-axis scaling (auto/manual) are maintained.
*   Verify initial Y-axis auto-scaling and its dynamic adjustment with time-scale zoom/pan.
*   Test manual Y-axis min/max input: set values, validate input, and observe interaction with X-axis zoom.
*   Test "Reset Y-Axis Range" button: verify return to auto-scaling and clearing of input fields.
*   Ensure that all chart interactions do not negatively impact the performance or stability of the application.

## 6. Layer Management Feature Specification

### 6.1 Feature Description
This feature allows users to overlay different data series or visual elements onto the K-line chart, such as trading signals, indicator lines, and event markers. Each layer can be independently toggled on/off, styled, or configured.

### 6.2 Initial Options
*   **Default Layer**: The K-line chart itself serves as the base layer.
*   **Selectable Layer Types**:
    *   **交易資料圖層 (Trade Data Layer)**: 在 K 線圖上顯示買入/賣出交易點，以特定圖示（例如：箭頭）標示，並可顯示相關資訊（如價格、數量、備註）。
    *   **移動平均線 (MA)**: 不同週期的移動平均線。
    *   **成交量 (Volume)**: 顯示在圖表底部的獨立成交量圖。
    *   **布林通道 (Bollinger Bands)**: 顯示布林通道的上下軌和中軌。
    *   **自訂指標 (Custom Indicators)**: 未來可擴展用於其他技術指標（例如：RSI, MACD）。
    *   **事件標記 (Event Markers)**: 用於特定日期或時間點的文字/圖示標記。

### 6.3 User Interface (UI) Design
*   **Layer Control Panel**: Add an expandable/collapsible panel above or to the side of the chart, listing all available layers.
*   **Layer Toggles**: Each layer should have a checkbox or toggle switch to control its visibility.
*   **Layer Settings**: A gear icon or dropdown menu next to each layer can provide options to adjust its style (e.g., line color, thickness, marker icon) or parameters (e.g., MA period).

### 6.4 Implementation Details (Internal)
*   **Data Structure Definition**: Define a data structure for layers, including `id`, `name`, `type`, `isVisible`, and `settings` (e.g., `color`, `period`).
*   **Layer State Management**: Manage the state of active layers and their configurations within `KlineChart.vue` or a state management solution (if used).
*   **UI Component Development**: Create a new Vue component (e.g., `LayerControl.vue`) to display the layer list and control options. This component will emit events to `KlineChart.vue` when layer states change.
*   **`lightweight-charts` API Integration**: `KlineChart.vue` will dynamically create, update, or remove layers using the `lightweight-charts` API based on the state received from `LayerControl.vue`.
    *   **Base K-line Chart**: Serves as the main series and cannot be turned off.
    *   **Overlay Series**: New `series` (e.g., `chart.addLineSeries()`, `chart.addHistogramSeries()`) will be created for moving averages, trading signals, etc. Series properties (e.g., color, line width) will be configured dynamically based on layer settings. Trading signals might use `chart.timeScale().createPriceLine()` or `series.setMarkers()`.
    *   **Data Loading**: Ensure that data required for different layers (e.g., MA calculation results, trading signal data) is correctly loaded and passed to `lightweight-charts`.
    *   **6.4.1 交易資料圖層實作細節 (Trading Data Layer Implementation Details)**
        *   **後端 API (`server.py`)**:
            *   新增 `/api/trade_data` 端點，接收 `start_time` 和 `end_time` (Unix timestamp) 參數。
            *   查詢 `trade_notes.db` 中的 `trades` 表，根據時間範圍篩選交易記錄。
            *   為每個交易記錄，結合 `market_data` 表獲取該時間點的 `close` 價格作為標記的價格位置。若無精確匹配，則取最近的 K 線收盤價。
            *   返回資料格式包含 `time` (Unix timestamp), `price`, `action` (buy/sell), 及 `text` (顯示內容)。
        *   **前端實作 (`KlineChart.vue`)**:
            *   引入 `showTradeData` (boolean) 和 `tradeData` (array) 響應式變數。
            *   在圖表工具列新增「交易資料」Checkbox，綁定 `showTradeData`。
            *   實作 `fetchTradeData(startTime, endTime)` 非同步函數，呼叫後端 `/api/trade_data`。
            *   實作 `drawTradeData()` 函數：
                *   根據 `showTradeData` 狀態決定是否顯示交易標記。
                *   將 `tradeData` 轉換為 `lightweight-charts` 的 `marker` 格式。
                *   使用 `candlestickSeries.setMarkers()` 來設置買入（綠色箭頭向上, `belowBar`）和賣出（紅色箭頭向下, `aboveBar`）標記。
            *   在 `setupChart()`、`updateChartData()` 和 `onMounted()` 中適時呼叫 `fetchTradeData` 和 `drawTradeData` 以確保資料載入與顯示同步。
    *   **Styling and Interactivity**: Ensure the layer control panel's styling is consistent with the existing interface and that real-time chart updates occur when layer toggles or settings are changed.*   **Backend (if applicable)**: If some complex indicators require backend calculation, new API endpoints will be defined for frontend consumption.

### 6.5 Testing
*   Verify that new layers can be added and removed from the chart.
*   Test toggling the visibility of each layer.
*   Verify that changing layer settings (e.g., MA period, color) correctly updates the chart.
*   Ensure that multiple layers can be displayed simultaneously without conflicts.
*   Test the performance implications of adding multiple layers.
*   Confirm data consistency across layers when the underlying K-line data changes.