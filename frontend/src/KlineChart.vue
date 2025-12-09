<template>
  <div class="kline-chart-container">
    <h3>{{ $t('kline_chart_title') }}</h3>
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
const API_BASE_URL = 'http://localhost:8000'; // Define the correct API base URL
const chartContainer = ref(null);
let chart = null;
const isLoading = ref(true);
const hasData = ref(false);

const fetchData = async () => {
  isLoading.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/kline_data`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();
    
    if (data && data.length > 0) {
      hasData.value = true;
      return data;
    } else {
      hasData.value = false;
      return [];
    }
  } catch (error) {
    console.error("Failed to fetch K-line data:", error);
    hasData.value = false;
    return [];
  } finally {
    isLoading.value = false;
  }
};

const setupChart = (data) => {
  if (!chartContainer.value || data.length === 0) return;

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
    },
  });

  const candlestickSeries = chart.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderDownColor: '#ef5350',
    borderUpColor: '#26a69a',
    wickDownColor: '#ef5350',
    wickUpColor: '#26a69a',
  });

  candlestickSeries.setData(data);

  const volumeSeries = chart.addHistogramSeries({
    color: '#26a69a',
    priceFormat: {
      type: 'volume',
    },
    pane: 0, // Explicitly set to the main chart pane
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
};

const resizeHandler = () => {
  if (chart && chartContainer.value) {
    chart.resize(chartContainer.value.clientWidth, 500);
  }
};

onMounted(async () => {
  const data = await fetchData();
  if (hasData.value) {
    await nextTick();
    setupChart(data);
    window.addEventListener('resize', resizeHandler);
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
