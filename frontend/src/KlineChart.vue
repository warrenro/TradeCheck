<template>
  <div class="kline-chart-container">
    <h3>{{ $t('kline_chart_title') }}</h3>
    <div class="chart-toolbar">
      <label for="timeframe-select">{{ $t('timeframe') }}: </label>
      <select id="timeframe-select" v-model="selectedTimeframe" @change="updateChartData">
        <option value="1T">{{ $t('1_minute') }}</option>
        <option value="5T">{{ $t('5_minutes') }}</option>
        <option value="15T">{{ $t('15_minutes') }}</option>
        <option value="1H">{{ $t('1_hour') }}</option>
        <option value="1D">{{ $t('1_day') }}</option>
      </select>

      <label class="indicator-checkbox">
        <input type="checkbox" v-model="showMA5" @change="drawIndicators"> MA5
      </label>
      <label class="indicator-checkbox">
        <input type="checkbox" v-model="showMA10" @change="drawIndicators"> MA10
      </label>
      <label class="indicator-checkbox">
        <input type="checkbox" v-model="showMA20" @change="drawIndicators"> MA20
      </label>
      <label class="indicator-checkbox">
        <input type="checkbox" v-model="showMA60" @change="drawIndicators"> MA60
      </label>
      <label class="indicator-checkbox">
        <input type="checkbox" v-model="showBBands" @change="drawIndicators"> Bollinger Bands
      </label>
      <label class="indicator-checkbox">
        <input type="checkbox" v-model="showTradeData" @change="drawTradeData"> {{ $t('trade_data_layer') }}
      </label>

      <button @click="setChartType('Candlestick')" :class="{ 'active': currentChartType === 'Candlestick' }">Candlestick</button>
      <button @click="setChartType('Line')" :class="{ 'active': currentChartType === 'Line' }">Line</button>

      <button @click="exportChart" class="export-button">{{ $t('export_chart') }}</button>
      
      <button @click="zoomIn" class="zoom-button">{{ $t('zoom_in') }}</button>
      <button @click="zoomOut" class="zoom-button">{{ $t('zoom_out') }}</button>
      <button @click="resetZoom" class="zoom-button">{{ $t('reset_zoom') }}</button>

      <label for="y-min-input">{{ $t('y_axis_min') }}: </label>
      <input type="number" id="y-min-input" v-model.number="manualYAxisMin" placeholder="Auto" />
      <label for="y-max-input">{{ $t('y_axis_max') }}: </label>
      <input type="number" id="y-max-input" v-model.number="manualYAxisMax" placeholder="Auto" />
      <button @click="setManualYAxisRange">{{ $t('set_y_range') }}</button>
      <button @click="resetYAxisRange">{{ $t('reset_y_range') }}</button>
    </div>
    <div ref="chartContainer" class="chart-container"></div>
    <div v-if="isLoading" class="loading-overlay">{{ $t('loading_data') }}</div>
    <div v-if="!isLoading && !hasData" class="loading-overlay">{{ $t('no_kline_data') }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { createChart } from 'lightweight-charts';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const API_BASE_URL = 'http://localhost:8000';
const chartContainer = ref(null);
let chart = null;
let candlestickSeries = null;
let lineSeries = null; // New series for line chart
let volumeSeries = null;

// Indicator series refs
let ma5Series = null;
let ma10Series = null;
let ma20Series = null;
let ma60Series = null;
let bbandsUpperSeries = null;
let bbandsMiddleSeries = null;
let bbandsLowerSeries = null;

const isLoading = ref(true);
const hasData = ref(false);
const selectedTimeframe = ref('1T');

// Indicator visibility states
const showMA5 = ref(false);
const showMA10 = ref(false);
const showMA20 = ref(false);
const showMA60 = ref(false);
const showBBands = ref(false);
const showTradeData = ref(false); // New: visibility state for trade data
const tradeData = ref([]); // New: Store fetched trade data
const currentChartType = ref('Candlestick'); // Default chart type

const currentChartData = ref([]); // Store the fetched data for indicator calculations
const firstDataTime = ref(null);
const lastDataTime = ref(null);
const manualYAxisMin = ref(null); // For manual Y-axis minimum input
const manualYAxisMax = ref(null); // For manual Y-axis maximum input

const fetchData = async (timeframe) => {
  isLoading.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/kline_data?timeframe=${timeframe}`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();
    
    if (data && data.length > 0) {
      hasData.value = true;
      currentChartData.value = data; // Store data
      firstDataTime.value = data[0].time; // Assuming data is sorted by time
      lastDataTime.value = data[data.length - 1].time;
      return data;
    } else {
      hasData.value = false;
      currentChartData.value = [];
      firstDataTime.value = null;
      lastDataTime.value = null;
      return [];
    }
  } catch (error) {
    console.error("Failed to fetch K-line data:", error);
    hasData.value = false;
    currentChartData.value = [];
    firstDataTime.value = null;
    lastDataTime.value = null;
    return [];
  } finally {
    isLoading.value = false;
  }
};

const fetchTradeData = async (startTime, endTime) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/trade_data?start_time=${startTime}&end_time=${endTime}`);
    if (!response.ok) {
      throw new Error('Network response for trade data was not ok');
    }
    const data = await response.json();
    tradeData.value = data;
  } catch (error) {
    console.error("Failed to fetch trade data:", error);
    tradeData.value = [];
  }
};

// ... existing code ...

const setupChart = (data) => {
  if (!chartContainer.value || data.length === 0) return;

  if (chart) {
    chart.remove();
    chart = null;
    // Null out series refs after chart is destroyed
    candlestickSeries = null;
    lineSeries = null;
    volumeSeries = null;
    ma5Series = null;
    ma10Series = null;
    ma20Series = null;
    ma60Series = null;
    bbandsUpperSeries = null;
    bbandsMiddleSeries = null;
    bbandsLowerSeries = null;
  }

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: 500,
    layout: {
      backgroundColor: '#ffffff',
      textColor: 'rgba(33, 56, 77, 1)',
    },
    grid: {
      vertLines: {
        color: 'rgba(197, 203, 206, 0.5)',
      },
      horzLines: {
        color: 'rgba(197, 203, 206, 0.5)',
      },
    },
    crosshair: {
      mode: 'normal',
    },
    timeScale: {
      borderColor: 'rgba(197, 203, 206, 0.8)',
      // Ensure the entire range of data is visible by default
      // This is crucial for fitContent() to work as expected on initial load
      barSpacing: 6, // Set a default bar spacing to ensure visible bar width
    },
    // Explicitly enable mouse wheel zoom and drag-to-pan
    handleScroll: {
      vertTouchDrag: true,
      horzTouchDrag: true,
      mouseWheel: true,
      pressedMouseMove: true,
    },
    handleScale: {
      axisDoubleClickReset: true,
      mouseWheel: true,
      pinch: true,
    },
    priceScale: { // 全局價格軸設定，確保自動縮放行為
      autoScale: true,
      scaleMargins: {
        top: 0.1, // 10% space above the highest point
        bottom: 0.1, // 10% space below the lowest point
      },
    },
  });

  // Remove existing series before adding new ones
  if (candlestickSeries) chart.removeSeries(candlestickSeries);
  if (lineSeries) chart.removeSeries(lineSeries);
  if (volumeSeries) chart.removeSeries(volumeSeries);

  if (currentChartType.value === 'Candlestick') {
    candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderDownColor: '#ef5350',
      borderUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      wickUpColor: '#26a69a',
    });
    candlestickSeries.setData(data);
    candlestickSeries.priceScale().applyOptions(mainSeriesPriceScaleOptions); // Apply to candlestick series
  } else if (currentChartType.value === 'Line') {
    lineSeries = chart.addLineSeries({
      color: '#2196F3', // Blue color for line chart
      lineWidth: 2,
    });
    // For a line chart, we typically use the close price
    const lineData = data.map(d => ({ time: d.time, value: d.close }));
    lineSeries.setData(lineData);
    lineSeries.priceScale().applyOptions(mainSeriesPriceScaleOptions); // Apply to line series
  }

  volumeSeries = chart.addHistogramSeries({
    color: '#26a69a',
    priceFormat: {
      type: 'volume',
    },
    pane: 0,
  });

  volumeSeries.priceScale().applyOptions({
      scaleMargins: {
          top: 0.8,
          bottom: 0,
      }
  })

  const volumeData = data.map(d => ({
    time: d.time,
    value: d.value,
    color: d.close > d.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)',
  }));
  
  volumeSeries.setData(volumeData);

  chart.timeScale().fitContent();

  drawIndicators(); // Draw indicators after setting up the main chart
  drawTradeData(); // New: Draw trade data after setting up the chart
};

const drawIndicators = () => {
  if (!chart || currentChartData.value.length === 0) return;

  // Clear existing indicator series
  if (ma5Series) { chart.removeSeries(ma5Series); ma5Series = null; }
  if (ma10Series) { chart.removeSeries(ma10Series); ma10Series = null; }
  if (ma20Series) { chart.removeSeries(ma20Series); ma20Series = null; }
  if (ma60Series) { chart.removeSeries(ma60Series); ma60Series = null; }
  if (bbandsUpperSeries) { chart.removeSeries(bbandsUpperSeries); bbandsUpperSeries = null; }
  if (bbandsMiddleSeries) { chart.removeSeries(bbandsMiddleSeries); bbandsMiddleSeries = null; }
  if (bbandsLowerSeries) { chart.removeSeries(bbandsLowerSeries); bbandsLowerSeries = null; }

  // Draw MA5
  if (showMA5.value) {
    const maData = calculateMA(currentChartData.value, 5);
    ma5Series = chart.addLineSeries({ color: 'blue', lineWidth: 1, title: 'MA5' });
    ma5Series.setData(maData);
  }

  // Draw MA10
  if (showMA10.value) {
    const maData = calculateMA(currentChartData.value, 10);
    ma10Series = chart.addLineSeries({ color: 'purple', lineWidth: 1, title: 'MA10' });
    ma10Series.setData(maData);
  }

  // Draw MA20
  if (showMA20.value) {
    const maData = calculateMA(currentChartData.value, 20);
    ma20Series = chart.addLineSeries({ color: 'orange', lineWidth: 1, title: 'MA20' });
    ma20Series.setData(maData);
  }

  // Draw MA60
  if (showMA60.value) {
    const maData = calculateMA(currentChartData.value, 60);
    ma60Series = chart.addLineSeries({ color: 'red', lineWidth: 1, title: 'MA60' });
    ma60Series.setData(maData);
  }

  // Draw Bollinger Bands
  if (showBBands.value) {
    const bbandsData = calculateBBands(currentChartData.value, 20, 2);
    bbandsUpperSeries = chart.addLineSeries({ color: 'green', lineWidth: 1, lineStyle: 2, title: 'BB Upper' });
    bbandsMiddleSeries = chart.addLineSeries({ color: 'green', lineWidth: 1, lineStyle: 1, title: 'BB Middle' });
    bbandsLowerSeries = chart.addLineSeries({ color: 'green', lineWidth: 1, lineStyle: 2, title: 'BB Lower' });
    bbandsUpperSeries.setData(bbandsData.upper);
    bbandsMiddleSeries.setData(bbandsData.middle);
    bbandsLowerSeries.setData(bbandsData.lower);
  }
};

const drawTradeData = () => {
  // Ensure we have a series to attach markers to
  const targetSeries = candlestickSeries || lineSeries;
  if (!chart || !targetSeries) { // No need to check tradeData.value.length here, as it might be empty on purpose
    if (targetSeries) targetSeries.setMarkers([]); // Clear markers if conditions not met
    return;
  }

  if (showTradeData.value && tradeData.value.length > 0) {
    // Map fetched tradeData to lightweight-charts marker format
    const markers = tradeData.value.map(trade => ({
      time: trade.time,
      position: trade.action.toLowerCase() === 'buy' ? 'belowBar' : 'aboveBar',
      color: trade.action.toLowerCase() === 'buy' ? '#26a69a' : '#ef5350', // Green for buy, Red for sell
      shape: trade.action.toLowerCase() === 'buy' ? 'arrowUp' : 'arrowDown',
      text: trade.text || '' // Use the text generated by the backend
    }));
    targetSeries.setMarkers(markers);
  } else {
    targetSeries.setMarkers([]); // Clear all markers
  }
};

const updateChartData = async () => {
  const data = await fetchData(selectedTimeframe.value);
  if (hasData.value) {
    await nextTick();
    setupChart(data); // setupChart will call drawIndicators and drawTradeData
    // Also fetch trade data for the current K-line data range
    if (firstDataTime.value && lastDataTime.value) {
      await fetchTradeData(firstDataTime.value, lastDataTime.value);
      drawTradeData(); // Redraw trade data after fetching
    }
  }
};

const setChartType = (type) => {
  if (currentChartType.value !== type) {
    currentChartType.value = type;
    setupChart(currentChartData.value); // Re-setup chart with new type
  }
};

const zoomFactor = 0.2; // 20% zoom in/out
const MIN_VISIBLE_BARS = 5; // Minimum number of bars to be visible when zooming in

const zoomIn = () => {
  if (!chart || currentChartData.value.length === 0 || !firstDataTime.value || !lastDataTime.value) {
    return;
  }

  const visibleRange = chart.timeScale().getVisibleRange();
  if (!visibleRange) {
    return;
  }

  const duration = visibleRange.to - visibleRange.from;
  let newDuration = duration * (1 - zoomFactor);

  // Ensure minimum visible bars
  // Approximate the duration of one bar based on the total data range and number of bars
  const totalDataDuration = lastDataTime.value - firstDataTime.value;
  const avgBarDuration = totalDataDuration / currentChartData.value.length;
  const minDuration = MIN_VISIBLE_BARS * avgBarDuration;

  if (newDuration < minDuration) {
    newDuration = minDuration;
  }

  const center = visibleRange.from + duration / 2;
  let newFrom = center - newDuration / 2;
  let newTo = center + newDuration / 2;

  // Clamp to overall data range if necessary to prevent empty space
  if (newFrom < firstDataTime.value) {
    newFrom = firstDataTime.value;
    newTo = firstDataTime.value + newDuration;
  }
  if (newTo > lastDataTime.value) {
    newTo = lastDataTime.value;
    newFrom = lastDataTime.value - newDuration;
  }

  // Final check to ensure newFrom doesn't exceed newTo after clamping
  if (newFrom > newTo) {
      newFrom = newTo - newDuration; // Adjust newFrom to maintain duration
      if (newFrom < firstDataTime.value) newFrom = firstDataTime.value; // Clamp again if it goes too far
  }
  
  chart.timeScale().setVisibleRange({ from: newFrom, to: newTo });
};

const zoomOut = () => {
  if (!chart || currentChartData.value.length === 0 || !firstDataTime.value || !lastDataTime.value) {
    return;
  }

  const visibleRange = chart.timeScale().getVisibleRange();
  if (!visibleRange) {
    return;
  }

  const duration = visibleRange.to - visibleRange.from;
  let newDuration = duration * (1 + zoomFactor);

  // Ensure new duration doesn't exceed total data duration
  const totalDataDuration = lastDataTime.value - firstDataTime.value;
  if (newDuration > totalDataDuration) {
    newDuration = totalDataDuration;
  }

  const center = visibleRange.from + duration / 2;
  let newFrom = center - newDuration / 2;
  let newTo = center + newDuration / 2;

  // Clamp to overall data range
  if (newFrom < firstDataTime.value) {
    newFrom = firstDataTime.value;
    newTo = firstDataTime.value + newDuration;
  }
  if (newTo > lastDataTime.value) {
    newTo = lastDataTime.value;
    newFrom = lastDataTime.value - newDuration;
  }

  // If after clamping, newFrom still pushes newTo beyond the max, adjust newFrom again
  // This can happen if newDuration equals totalDataDuration and newTo was slightly off
  if (newTo - newFrom > totalDataDuration) {
      newFrom = firstDataTime.value;
      newTo = lastDataTime.value;
  }
  
  chart.timeScale().setVisibleRange({ from: newFrom, to: newTo });
};

const setManualYAxisRange = () => {
  if (!chart) return;

  const newMin = manualYAxisMin.value !== null && !isNaN(manualYAxisMin.value) ? parseFloat(manualYAxisMin.value) : null;
  const newMax = manualYAxisMax.value !== null && !isNaN(manualYAxisMax.value) ? parseFloat(manualYAxisMax.value) : null;

  if (newMin === null && newMax === null) {
    alert(t('invalid_y_range_input')); // Neither min nor max provided
    return;
  }

  // Basic validation: max must be greater than min if both are provided
  if (newMin !== null && newMax !== null && newMax <= newMin) {
    alert(t('y_max_less_than_y_min')); // Max not greater than min
    return;
  }

  const priceScaleOptions = {
    autoScale: false,
    scaleMargins: {
      top: 0.1,
      bottom: 0.1,
    },
    minimum: newMin !== null ? newMin : undefined,
    maximum: newMax !== null ? newMax : undefined,
  };

  if (currentChartType.value === 'Candlestick' && candlestickSeries) {
    candlestickSeries.priceScale().applyOptions(priceScaleOptions);
  } else if (currentChartType.value === 'Line' && lineSeries) {
    lineSeries.priceScale().applyOptions(priceScaleOptions);
  }
};

const resetYAxisRange = () => {
  manualYAxisMin.value = null; // Clear the input
  manualYAxisMax.value = null; // Clear the input

  const priceScaleOptions = {
    autoScale: true, // Re-enable auto-scaling
    scaleMargins: {
        top: 0.1,
        bottom: 0.1,
    },
    // Remove explicit max/min as autoScale will handle it
    maximum: undefined,
    minimum: undefined,
  };

  if (currentChartType.value === 'Candlestick' && candlestickSeries) {
    candlestickSeries.priceScale().applyOptions(priceScaleOptions);
  } else if (currentChartType.value === 'Line' && lineSeries) {
    lineSeries.priceScale().applyOptions(priceScaleOptions);
  }
};

const exportChart = () => {
  if (chart) {
    const img = document.createElement('img');
    img.src = chart.takeScreenshot();

    const a = document.createElement('a');
    a.href = img.src;
    a.download = `kline_chart_${selectedTimeframe.value}_${new Date().toISOString().slice(0, 10)}.png`;
    a.click();
  }
};

const resizeHandler = () => {
  if (chart && chartContainer.value) {
    chart.resize(chartContainer.value.clientWidth, 500);
    chart.timeScale().fitContent(); // Also fit content when resizing
  }
};

onMounted(async () => {
  const data = await fetchData(selectedTimeframe.value);
  if (hasData.value) {
    await nextTick();
    setupChart(data);
    window.addEventListener('resize', resizeHandler);
    // Initial fetch of trade data
    if (firstDataTime.value && lastDataTime.value) {
      await fetchTradeData(firstDataTime.value, lastDataTime.value);
      drawTradeData();
    }
  }
});

onBeforeUnmount(() => {
  if (chart) {
    chart.remove();
    chart = null;
  }
  window.removeEventListener('resize', resizeHandler);
});

</script>

<style scoped>
.kline-chart-container {
  margin-top: 20px;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
  position: relative;
}
.chart-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
  flex-wrap: wrap; /* Allow items to wrap on smaller screens */
  align-items: center;
}
.chart-container {
  width: 100%;
  height: 500px;
}
.loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 1.2em;
}
</style>
