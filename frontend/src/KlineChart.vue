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
        <input type="checkbox" v-model="showTradeData" @change="toggleTradeDataLayer"> {{ $t('trade_data_layer') }}
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
let lineSeries = null;
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
const showTradeData = ref(false);
const tradeData = ref([]);
const currentChartType = ref('Candlestick');

const currentChartData = ref([]);
const firstDataTime = ref(null);
const lastDataTime = ref(null);
const manualYAxisMin = ref(null);
const manualYAxisMax = ref(null);

const calculateMA = (data, period) => {
  let result = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push({ time: data[i].time, value: undefined });
    } else {
      let sum = 0;
      for (let j = 0; j < period; j++) {
        sum += data[i - j].close;
      }
      result.push({ time: data[i].time, value: sum / period });
    }
  }
  return result;
};

const calculateBBands = (data, period = 20, stdDev = 2) => {
  let upper = [];
  let middle = [];
  let lower = [];

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      upper.push({ time: data[i].time, value: undefined });
      middle.push({ time: data[i].time, value: undefined });
      lower.push({ time: data[i].time, value: undefined });
    } else {
      let slice = data.slice(i - period + 1, i + 1);
      let sma = slice.reduce((acc, val) => acc + val.close, 0) / period;
      
      let stdDevValue = Math.sqrt(
        slice.reduce((acc, val) => acc + Math.pow(val.close - sma, 2), 0) / period
      );

      middle.push({ time: data[i].time, value: sma });
      upper.push({ time: data[i].time, value: sma + stdDev * stdDevValue });
      lower.push({ time: data[i].time, value: sma - stdDev * stdDevValue });
    }
  }
  return { upper, middle, lower };
};

const fetchData = async (timeframe) => {
  isLoading.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/kline_data?timeframe=${timeframe}`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();

    // **Defensive Data Cleaning**
    const cleanedData = data.filter(d => 
      d && typeof d.time === 'number' &&
      typeof d.high === 'number' && isFinite(d.high) && d.high > 0 &&
      typeof d.low === 'number' && isFinite(d.low) && d.low > 0 &&
      typeof d.open === 'number' && isFinite(d.open) && d.open > 0 &&
      typeof d.close === 'number' && isFinite(d.close) && d.close > 0
    );

    if (cleanedData.length !== data.length) {
      console.warn(`Data cleaning removed ${data.length - cleanedData.length} invalid records.`);
    }
    
    if (cleanedData && cleanedData.length > 0) {
      hasData.value = true;
      currentChartData.value = cleanedData;
      firstDataTime.value = cleanedData[0].time;
      lastDataTime.value = cleanedData[cleanedData.length - 1].time;
      return cleanedData;
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
    tradeData.value = await response.json();
  } catch (error) {
    console.error("Failed to fetch trade data:", error);
    tradeData.value = [];
  }
};

const setupChart = (data) => {
  if (!chartContainer.value || data.length === 0) return;

  if (chart) {
    chart.remove();
    chart = null;
  }
  
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

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: 500,
    layout: {
      backgroundColor: '#ffffff',
      textColor: 'rgba(33, 56, 77, 1)',
    },
    grid: {
      vertLines: { color: 'rgba(197, 203, 206, 0.5)' },
      horzLines: { color: 'rgba(197, 203, 206, 0.5)' },
    },
    crosshair: { mode: 'normal' },
    timeScale: {
      borderColor: 'rgba(197, 203, 206, 0.8)',
      barSpacing: 6,
    },
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
    priceScale: {
      autoScale: true,
      scaleMargins: { top: 0.1, bottom: 0.2 },
      // ** THE DEFINITIVE FIX **
      autoscaleInfoProvider: () => {
        const visibleRange = chart ? chart.timeScale().getVisibleRange() : null;
        if (!visibleRange || !currentChartData.value || currentChartData.value.length === 0) {
            return null;
        }

        let minPrice = Infinity;
        let maxPrice = -Infinity;

        const visibleCandleData = currentChartData.value.filter(d => d.time >= visibleRange.from && d.time <= visibleRange.to);
        
        if (visibleCandleData.length > 0) {
            visibleCandleData.forEach(d => {
                minPrice = Math.min(minPrice, d.low);
                maxPrice = Math.max(maxPrice, d.high);
            });
        }

        const updatePriceRangeWithIndicator = (seriesData) => {
            if (!seriesData) return;
            const visibleSeriesData = seriesData.filter(d => d.time >= visibleRange.from && d.time <= visibleRange.to);
            visibleSeriesData.forEach(d => {
                if (d.value !== undefined && d.value !== null && !isNaN(d.value)) {
                    minPrice = Math.min(minPrice, d.value);
                    maxPrice = Math.max(maxPrice, d.value);
                }
            });
        };

        if (showMA5.value) updatePriceRangeWithIndicator(calculateMA(currentChartData.value, 5));
        if (showMA10.value) updatePriceRangeWithIndicator(calculateMA(currentChartData.value, 10));
        if (showMA20.value) updatePriceRangeWithIndicator(calculateMA(currentChartData.value, 20));
        if (showMA60.value) updatePriceRangeWithIndicator(calculateMA(currentChartData.value, 60));
        if (showBBands.value) {
            const bbands = calculateBBands(currentChartData.value, 20, 2);
            updatePriceRangeWithIndicator(bbands.upper);
            updatePriceRangeWithIndicator(bbands.middle);
            updatePriceRangeWithIndicator(bbands.lower);
        }
        
        if (minPrice === Infinity) return null;

        return {
            priceRange: {
                minValue: minPrice,
                maxValue: maxPrice,
            },
        };
      },
    },
  });

  if (currentChartType.value === 'Candlestick') {
    candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a', downColor: '#ef5350',
      borderDownColor: '#ef5350', borderUpColor: '#26a69a',
      wickDownColor: '#ef5350', wickUpColor: '#26a69a',
    });
    candlestickSeries.setData(data);
  } else {
    lineSeries = chart.addLineSeries({ color: '#2196F3', lineWidth: 2 });
    const lineData = data.map(d => ({ time: d.time, value: d.close }));
    lineSeries.setData(lineData);
  }

  // ** CORRECT VOLUME SERIES IMPLEMENTATION **
  volumeSeries = chart.addHistogramSeries({
    color: '#26a69a',
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume_scale', // Give it a separate price scale
  });
  volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
  });

  const volumeData = data.map(d => ({
    time: d.time,
    value: d.value,
    color: d.close > d.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)',
  }));
  volumeSeries.setData(volumeData);

  chart.timeScale().fitContent();

  chart.timeScale().subscribeVisibleTimeRangeChange(async () => {
    if (showTradeData.value) {
      const visibleRange = chart.timeScale().getVisibleRange();
      if (visibleRange) {
        await fetchTradeData(visibleRange.from, visibleRange.to);
        drawTradeData();
      }
    }
  });

  drawIndicators();
  drawTradeData();
};

const drawIndicators = () => {
  if (!chart) return;

  if (ma5Series) { chart.removeSeries(ma5Series); ma5Series = null; }
  if (ma10Series) { chart.removeSeries(ma10Series); ma10Series = null; }
  if (ma20Series) { chart.removeSeries(ma20Series); ma20Series = null; }
  if (ma60Series) { chart.removeSeries(ma60Series); ma60Series = null; }
  if (bbandsUpperSeries) { chart.removeSeries(bbandsUpperSeries); bbandsUpperSeries = null; }
  if (bbandsMiddleSeries) { chart.removeSeries(bbandsMiddleSeries); bbandsMiddleSeries = null; }
  if (bbandsLowerSeries) { chart.removeSeries(bbandsLowerSeries); bbandsLowerSeries = null; }

  const addIndicatorSeries = (data, options) => chart.addLineSeries({
      priceScaleId: 'right', // Ensure it's on the main price scale
      ...options,
  });

  if (showMA5.value) ma5Series = addIndicatorSeries(calculateMA(currentChartData.value, 5), { color: 'blue', lineWidth: 1, title: 'MA5' });
  if (showMA10.value) ma10Series = addIndicatorSeries(calculateMA(currentChartData.value, 10), { color: 'purple', lineWidth: 1, title: 'MA10' });
  if (showMA20.value) ma20Series = addIndicatorSeries(calculateMA(currentChartData.value, 20), { color: 'orange', lineWidth: 1, title: 'MA20' });
  if (showMA60.value) ma60Series = addIndicatorSeries(calculateMA(currentChartData.value, 60), { color: 'red', lineWidth: 1, title: 'MA60' });

  if (showBBands.value) {
    const bbandsData = calculateBBands(currentChartData.value, 20, 2);
    bbandsUpperSeries = addIndicatorSeries(bbandsData.upper, { color: 'green', lineWidth: 1, lineStyle: 2, title: 'BB Upper' });
    bbandsMiddleSeries = addIndicatorSeries(bbandsData.middle, { color: 'green', lineWidth: 1, lineStyle: 1, title: 'BB Middle' });
    bbandsLowerSeries = addIndicatorSeries(bbandsData.lower, { color: 'green', lineWidth: 1, lineStyle: 2, title: 'BB Lower' });
  }
  
  if (ma5Series) ma5Series.setData(calculateMA(currentChartData.value, 5));
  if (ma10Series) ma10Series.setData(calculateMA(currentChartData.value, 10));
  if (ma20Series) ma20Series.setData(calculateMA(currentChartData.value, 20));
  if (ma60Series) ma60Series.setData(calculateMA(currentChartData.value, 60));
  if (bbandsUpperSeries) {
      const bbandsData = calculateBBands(currentChartData.value, 20, 2);
      bbandsUpperSeries.setData(bbandsData.upper);
      bbandsMiddleSeries.setData(bbandsData.middle);
      bbandsLowerSeries.setData(bbandsData.lower);
  }
};

const drawTradeData = () => {
  const targetSeries = candlestickSeries || lineSeries;
  if (!chart || !targetSeries) return;

  if (showTradeData.value && tradeData.value.length > 0) {
    const markers = tradeData.value.map(trade => ({
      time: trade.time,
      position: trade.action.toLowerCase() === 'buy' ? 'belowBar' : 'aboveBar',
      color: trade.action.toLowerCase() === 'buy' ? 'blue' : '#FF0000',
      shape: trade.action.toLowerCase() === 'buy' ? 'arrowUp' : 'arrowDown',
      text: `${trade.action.toUpperCase()} @ ${trade.price}`
    }));
    targetSeries.setMarkers(markers);
  } else {
    targetSeries.setMarkers([]);
  }
};

const toggleTradeDataLayer = async () => {
  if (showTradeData.value) {
    const visibleRange = chart ? chart.timeScale().getVisibleRange() : null;
    if (visibleRange) {
      await fetchTradeData(visibleRange.from, visibleRange.to);
    }
  }
  drawTradeData();
};

const updateChartData = async () => {
  const data = await fetchData(selectedTimeframe.value);
  if (hasData.value) {
    await nextTick();
    setupChart(data);
  }
};

const setChartType = (type) => {
  if (currentChartType.value !== type) {
    currentChartType.value = type;
    setupChart(currentChartData.value);
  }
};

const zoomIn = () => {
  if (chart) chart.timeScale().zoomIn();
};

const zoomOut = () => {
  if (chart) chart.timeScale().zoomOut();
};

const resetZoom = () => {
    if(chart) chart.timeScale().fitContent();
}

const setManualYAxisRange = () => {
  if (!chart) return;
  const targetSeries = candlestickSeries || lineSeries;
  if (!targetSeries) return;

  const newMin = manualYAxisMin.value !== null && !isNaN(manualYAxisMin.value) ? parseFloat(manualYAxisMin.value) : null;
  const newMax = manualYAxisMax.value !== null && !isNaN(manualYAxisMax.value) ? parseFloat(manualYAxisMax.value) : null;

  if (newMin !== null && newMax !== null && newMax <= newMin) {
    alert(t('y_max_less_than_y_min'));
    return;
  }

  targetSeries.priceScale().applyOptions({
    autoScale: false,
    minimum: newMin,
    maximum: newMax,
  });
};

const resetYAxisRange = () => {
  const targetSeries = candlestickSeries || lineSeries;
  if (targetSeries) {
    manualYAxisMin.value = null;
    manualYAxisMax.value = null;
    targetSeries.priceScale().applyOptions({ autoScale: true });
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
  }
};

onMounted(async () => {
  await updateChartData();
  window.addEventListener('resize', resizeHandler);
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