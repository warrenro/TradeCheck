<template>
  <main>
    <!-- Header -->
    <div class="header-container">
      <header>
        <h1>{{ $t('header.title') }}</h1>
      </header>
      <div class="status-container">
        <div class="server-status">
          <span :class="['status-dot', serverStatus]"></span>
          <span class="status-text">{{ $t('header.backendStatus') }}: <strong>{{ serverStatus === 'online' ? $t('header.online') : $t('header.offline') }}</strong></span>
        </div>
        <div class="lang-switcher">
          <select v-model="$i18n.locale">
            <option value="zh-TW">繁體中文</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
    </div>

    <div class="container">
      <!-- Left side: File Selection -->
      <div class="form-section">
        <div class="card">
          <div class="card-header">
            <h2><span class="step">1</span> {{ $t('form.selectFileTitle') }}</h2>
          </div>
          <div class="card-body">
            <div class="form-group">
              <label for="trade_file_select">{{ $t('form.selectFileTitle') }}</label>
              <select id="trade_file_select" v-model="selectedFile" :disabled="loading">
                <option v-if="tradeFiles.length === 0" disabled value="">{{ $t('form.loadingFiles') }}</option>
                <option v-for="file in tradeFiles" :key="file" :value="file">
                  {{ file }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <button @click="startAnalysis" :disabled="loading || !selectedFile" class="analyze-button">
                {{ loading ? $t('form.analyzing') : $t('form.analyzeButton') }}
              </button>
            </div>
             <p v-if="!loading" class="file-selection-note">{{ $t('form.clickToAnalyze') }}</p>
          </div>
        </div>
      </div>

      <!-- Right side: Dashboard Display -->
      <div class="dashboard-section">
        <div v-if="error" class="error-box">
          <strong>{{ $t('error.title') }}</strong> {{ errorDisplay }}
        </div>
        <div v-if="loading" class="loading-box">
          <p>{{ $t('loading') }}</p>
        </div>

        <div v-if="report" id="report-dashboard">
          <!-- Report Metadata -->
          <div class="card full-width-card report-meta">
            <div class="meta-item">
              <span>{{ $t('dashboard.meta.interval') }}:</span>
              <strong>{{ report.startDate }} &mdash; {{ report.endDate }}</strong>
            </div>
            <div class="meta-item">
              <span>{{ $t('dashboard.meta.generated') }}:</span>
              <strong>{{ new Date(report.generatedAt).toLocaleString() }}</strong>
            </div>
          </div>

          <!-- KPI Metrics Row -->
          <div class="kpi-grid">
            <div class="kpi-card">
              <h4>{{ $t('dashboard.kpi.winRate') }}</h4>
              <p :class="getKpiClass(report.account_summary.kpi_metrics.win_rate, 'wr')">{{ report.account_summary.kpi_metrics.win_rate }}</p>
            </div>
            <div class="kpi-card">
              <h4>{{ $t('dashboard.kpi.rr') }}</h4>
              <p :class="getKpiClass(report.account_summary.kpi_metrics.risk_reward_ratio, 'rr')">{{ report.account_summary.kpi_metrics.risk_reward_ratio }}</p>
            </div>
            <div class="kpi-card">
              <h4>{{ $t('dashboard.kpi.pnl') }}</h4>
              <p :class="getPnlClass(report.account_summary.monthly_pnl)">{{ formatCurrency(report.account_summary.monthly_pnl) }}</p>
            </div>
          </div>

          <!-- Other Cards -->
          <div class="card-grid">
            <!-- Account Status -->
            <div class="card">
              <div class="card-header"><h3>{{ $t('dashboard.accountStatus.title') }}</h3></div>
              <div class="card-body">
                <div class="status-item"><span>{{ $t('dashboard.accountStatus.currentScale') }}</span> <strong>{{ report.account_summary.scale }}</strong></div>
                <div class="status-item"><span>{{ $t('dashboard.accountStatus.monthlyStartCapital') }}</span> <strong>{{ formatCurrency(report.account_summary.monthly_start_capital) }}</strong></div>
                <div class="status-item"><span>{{ $t('dashboard.accountStatus.balance') }}</span> <strong>{{ formatCurrency(report.account_summary.current_balance) }}</strong></div>
              </div>
            </div>
            <!-- Safety Checks -->
            <div class="card">
              <div class="card-header"><h3>{{ $t('dashboard.safetyChecks.title') }}</h3></div>
              <div class="card-body">
                <div class="status-item">
                  <span>{{ $t('dashboard.safetyChecks.dailyStop') }}</span>
                  <strong :class="report.risk_audit.daily_stop_violated_days > 0 ? 'text-danger' : 'text-success'">
                    {{ report.risk_audit.daily_stop_violated_days > 0 ? $t('dashboard.safetyChecks.violations.violated') : $t('dashboard.safetyChecks.violations.safe') }}
                  </strong>
                </div>
                <div class="status-item">
                  <span>{{ $t('dashboard.safetyChecks.monthlyBreaker') }}</span>
                  <strong :class="report.risk_audit.capital_circuit_breaker_status === 'BREACHED' ? 'text-danger' : 'text-success'">
                    {{ report.risk_audit.capital_circuit_breaker_status === 'BREACHED' ? $t('dashboard.safetyChecks.violations.breached') : $t('dashboard.safetyChecks.violations.safe') }}
                  </strong>
                </div>
                 <div v-if="report.risk_audit.night_session_violations.length > 0" class="violations">
                  <h5>{{ $t('dashboard.safetyChecks.violations.title') }}</h5>
                  <ul>
                    <li v-for="(v, i) in report.risk_audit.night_session_violations" :key="i">
                      {{ v.rule }} at {{ v.violation_time }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            <!-- Evaluation -->
            <div class="card">
              <div class="card-header"><h3>{{ $t('dashboard.evaluation.title') }}</h3></div>
              <div class="card-body">
                <div class="status-item">
                  <span>{{ $t('dashboard.evaluation.upgradeEligible') }}</span>
                  <strong :class="report.capital_assessment.upgrade_eligible ? 'text-success' : 'text-warning'">
                    {{ report.capital_assessment.upgrade_eligible ? $t('dashboard.evaluation.yes') : $t('dashboard.evaluation.no') }}
                  </strong>
                </div>
                <p class="reason"><strong>{{ $t('dashboard.evaluation.reason') }}</strong> {{ report.capital_assessment.reason }}</p>
                <hr>
                <div class="status-item">
                  <span>{{ $t('dashboard.evaluation.incentive') }}</span>
                   <strong :class="report.capital_assessment.happiness_incentive.eligible ? 'text-success' : 'text-warning'">
                     {{ report.capital_assessment.happiness_incentive.eligible ? $t('dashboard.evaluation.eligible') : $t('dashboard.evaluation.notEligible') }}
                   </strong>
                </div>
                <div v-if="report.capital_assessment.happiness_incentive.eligible">
                  <p class="incentive-amount">{{ formatCurrency(report.capital_assessment.happiness_incentive.amount) }}</p>
                  <p class="reason">{{ report.capital_assessment.happiness_incentive.distribution }}</p>
                </div>
                 <div v-else>
                  <p class="reason">{{ report.capital_assessment.happiness_incentive.status }}</p>
                </div>
              </div>
            </div>

            <!-- Monthly Summary -->
            <div class="card full-width-card">
              <div class="card-header"><h3>{{ $t('dashboard.monthlySummary.title') }}</h3></div>
              <div class="card-body">
                <table class="summary-table">
                  <thead>
                    <tr>
                      <th>{{ $t('dashboard.monthlySummary.month') }}</th>
                      <th>{{ $t('dashboard.monthlySummary.totalPnl') }}</th>
                      <th>{{ $t('dashboard.monthlySummary.winRate') }}</th>
                      <th>{{ $t('dashboard.monthlySummary.rr') }}</th>
                      <th>{{ $t('dashboard.monthlySummary.tradeCount') }}</th>
                      <th>{{ $t('dashboard.monthlySummary.riskCheck') }}</th>
                      <th>{{ $t('dashboard.monthlySummary.evaluation') }}</th>
                      <th>{{ $t('dashboard.monthlySummary.incentive') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="summary in report.historical_summary" :key="summary.month" @click="showMonthDetails(summary.month)" class="clickable-row">
                      <td>{{ summary.month }}</td>
                      <td :class="getPnlClass(summary.total_pnl)">{{ formatCurrency(summary.total_pnl) }}</td>
                      <td>{{ summary.win_rate }}</td>
                      <td>{{ summary.risk_reward_ratio }}</td>
                      <td>{{ summary.trade_count }}</td>
                      <td>
                        <span :class="summary.risk_audit.capital_circuit_breaker_status === 'BREACHED' || summary.risk_audit.daily_stop_violated_days > 0 ? 'text-danger' : 'text-success'">
                          {{ summary.risk_audit.capital_circuit_breaker_status === 'BREACHED' || summary.risk_audit.daily_stop_violated_days > 0 ? $t('dashboard.monthlySummary.violated') : $t('dashboard.monthlySummary.safe') }}
                        </span>
                      </td>
                      <td>
                        <span :class="summary.capital_assessment.upgrade_eligible ? 'text-success' : 'text-warning'">
                          {{ summary.capital_assessment.upgrade_eligible ? $t('dashboard.monthlySummary.eligible') : $t('dashboard.monthlySummary.notEligible') }}
                        </span>
                      </td>
                      <td>
                        <span :class="summary.happiness_incentive.eligible ? 'text-success' : (summary.happiness_incentive.status.includes('補考') ? 'text-warning' : '')">
                          {{ summary.happiness_incentive.eligible ? formatCurrency(summary.happiness_incentive.amount) : summary.happiness_incentive.status }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Annual Summary -->
            <div class="card full-width-card">
              <div class="card-header"><h3>{{ $t('dashboard.annualSummary.title') }}</h3></div>
              <div class="card-body">
                <div v-for="(yearSummary, year) in report.annual_summary" :key="year" class="annual-summary-year-block">
                  <h4>{{ year }} {{ $t('dashboard.annualSummary.yearSuffix') }}</h4>
                  <div class="kpi-grid">
                    <div class="kpi-card">
                      <h4>{{ $t('dashboard.kpi.pnl') }}</h4>
                      <p :class="getPnlClass(yearSummary.total_pnl)">{{ formatCurrency(yearSummary.total_pnl) }}</p>
                    </div>
                    <div class="kpi-card">
                      <h4>{{ $t('dashboard.kpi.winRate') }}</h4>
                      <p>{{ yearSummary.win_rate }}</p>
                    </div>
                    <div class="kpi-card">
                      <h4>{{ $t('dashboard.kpi.rr') }}</h4>
                      <p>{{ yearSummary.risk_reward_ratio }}</p>
                    </div>
                    <div class="kpi-card">
                      <h4>{{ $t('dashboard.annualSummary.tradeCount') }}</h4>
                      <p>{{ yearSummary.trade_count }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- SOP Risk Reference -->
            <div class="card full-width-card">
              <div class="card-header"><h3>{{ $t('dashboard.sopRisk.title') }}</h3></div>
              <div class="card-body">
                <table class="summary-table">
                  <thead>
                    <tr>
                      <th>{{ $t('dashboard.sopRisk.scale') }}</th>
                      <th>{{ $t('dashboard.sopRisk.capital') }}</th>
                      <th>{{ $t('dashboard.sopRisk.sopA_loss') }}</th>
                      <th>{{ $t('dashboard.sopRisk.sopA_risk') }}</th>
                      <th>{{ $t('dashboard.sopRisk.sopB_loss') }}</th>
                      <th>{{ $t('dashboard.sopRisk.sopB_risk') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in sopRiskData" :key="row.scale">
                      <td>{{ row.scale }}</td>
                      <td>{{ row.capital }}</td>
                      <td>{{ row.sopA_loss }}</td>
                      <td>{{ row.sopA_risk }}</td>
                      <td>{{ row.sopB_loss }}</td>
                      <td>{{ row.sopB_risk }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="!report && !loading && !error" class="placeholder-box">
          <p>{{ $t('dashboard.placeholder') }}</p>
        </div>
      </div>
    </div>

    <!-- Monthly Details Modal -->
    <div v-if="selectedMonth" class="modal-overlay" @click.self="closeMonthDetails">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ $t('details.title', { month: selectedMonth }) }}</h3>
          <button @click="closeMonthDetails" class="close-button">&times;</button>
        </div>
        <div class="modal-body">
          <table class="details-table">
            <thead>
              <tr>
                <th>{{ $t('details.tradeTime') }}</th>
                <th>{{ $t('details.action') }}</th>
                <th>{{ $t('details.netPnl') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="selectedMonthTrades.length === 0">
                <td colspan="3">{{ $t('details.noTrades') }}</td>
              </tr>
              <tr v-for="(trade, index) in selectedMonthTrades" :key="index">
                <td>{{ trade.trade_time }}</td>
                <td>{{ trade.action }}</td>
                <td :class="getPnlClass(trade.net_pnl)">{{ formatCurrency(trade.net_pnl) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const API_BASE_URL = 'http://localhost:8000';

// --- Remote Logger ---
const logToServer = async (level, message, context = {}) => {
  try {
    await fetch(`${API_BASE_URL}/api/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level, message, context }),
    });
  } catch (e) {
    console.error("CRITICAL: Failed to send log to server:", e);
  }
};

const logger = {
  info: (message, context) => logToServer('info', message, context),
  warn: (message, context) => logToServer('warn', message, context),
  error: (message, context) => logToServer('error', message, context),
};

// --- Refs and State ---
const report = ref(null);
const loading = ref(false);
const error = ref(null);
const errorMessage = ref('');
const serverStatus = ref('offline');
const selectedMonth = ref(null);
const tradeFiles = ref([]);
const selectedFile = ref('');
const upgradeCriteria = ref(null);
const sopRiskData = ref([
  { scale: 'S1', capital: '100,000 (起始)', sopA_loss: '75,000', sopA_risk: '75.0%', sopB_loss: '75,000', sopB_risk: '75.0%' },
  { scale: 'S2', capital: '200,000', sopA_loss: '75,000', sopA_risk: '37.5%', sopB_loss: '75,000', sopB_risk: '37.5%' },
  { scale: 'S3', capital: '400,000', sopA_loss: '75,000', sopA_risk: '18.8%', sopB_loss: '75,000', sopB_risk: '18.8%' },
  { scale: 'S4', capital: '600,000', sopA_loss: '300,000', sopA_risk: '50.0%', sopB_loss: '300,000', sopB_risk: '50.0%' },
  { scale: 'S5', capital: '800,000', sopA_loss: '300,000', sopA_risk: '37.5%', sopB_loss: '300,000', sopB_risk: '37.5%' },
  { scale: 'S6', capital: '1,600,000', sopA_loss: '300,000', sopA_risk: '18.8%', sopB_loss: '300,000', sopB_risk: '18.8%' },
  { scale: 'S7', capital: '3,600,000', sopA_loss: '300,000', sopA_risk: '8.3%', sopB_loss: '300,000', sopB_risk: '8.3%' },
  { scale: 'S8', capital: '4,800,000', sopA_loss: '300,000', sopA_risk: '6.3%', sopB_loss: '300,000', sopB_risk: '6.3%' },
  { scale: 'S9', capital: '6,000,000', sopA_loss: '300,000', sopA_risk: '5.0%', sopB_loss: '300,000', sopB_risk: '5.0%' },
  { scale: 'S10', capital: '9,600,000', sopA_loss: '300,000', sopA_risk: '3.1%', sopB_loss: '600,000', sopB_risk: '6.3%' },
  { scale: 'S11', capital: '16,000,000', sopA_loss: '300,000', sopA_risk: '1.9%', sopB_loss: '600,000', sopB_risk: '3.8%' },
  { scale: 'S12', capital: '20,000,000', sopA_loss: '300,000', sopA_risk: '1.5%', sopB_loss: '600,000', sopB_risk: '3.0%' },
  { scale: 'S13', capital: '33,600,000', sopA_loss: '300,000', sopA_risk: '0.9%', sopB_loss: '900,000', sopB_risk: '2.7%' },
]);

// --- Computed Properties ---
const errorDisplay = computed(() => {
  if (error.value === 'error.failed') {
    return t('error.failed', { message: errorMessage.value });
  }
  return error.value ? t(error.value) : '';
});

const selectedMonthTrades = computed(() => {
  if (!selectedMonth.value || !report.value || !report.value.detailed_trades) {
    return [];
  }
  return report.value.detailed_trades[selectedMonth.value] || [];
});

// --- Lifecycle Hooks ---
onMounted(() => {
  logger.info('Frontend application mounted and ready.');
  checkServerStatus();
  setInterval(checkServerStatus, 10000);
  fetchTradeFiles();
});

// --- Methods ---
const checkServerStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/status`);
    serverStatus.value = response.ok ? 'online' : 'offline';
  } catch (e) {
    serverStatus.value = 'offline';
  }
};

const fetchTradeFiles = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/list_trade_files`);
    if (!response.ok) throw new Error('Failed to fetch trade files list.');
    
    const data = await response.json();
    tradeFiles.value = data.files || [];
    logger.info(`Found ${tradeFiles.value.length} trade files.`);

    if (tradeFiles.value.length > 0) {
      selectedFile.value = tradeFiles.value[0]; // Select the newest file by default
    }
  } catch (e) {
    error.value = 'error.failed';
    errorMessage.value = e.message;
    logger.error('Could not fetch trade files.', { error: e.message });
  }
};

const startAnalysis = async () => {
  if (!selectedFile.value) return;

  loading.value = true;
  error.value = null;
  errorMessage.value = '';
  // Do not clear the report, so the old one stays visible until the new one loads
  selectedMonth.value = null;

  logger.info(`Recalculating audit for file: ${selectedFile.value}`);

  try {
    const response = await fetch(`${API_BASE_URL}/api/run_check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: selectedFile.value }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP error! status: ${response.status}`);
    }
    report.value = data;
    logger.info(`Audit recalculation successful for ${selectedFile.value}.`);
  } catch (e) {
    error.value = 'error.failed';
    errorMessage.value = e.message;
    report.value = null; // Clear report on error
    logger.error(`Audit recalculation failed for ${selectedFile.value}.`, { error: e.message, stack: e.stack });
  } finally {
    loading.value = false;
  }
};

const showMonthDetails = (month) => {
  logger.info(`User requested details for month: ${month}`);
  selectedMonth.value = month;
};

const closeMonthDetails = () => {
  selectedMonth.value = null;
};

const formatCurrency = (value) => {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'TWD', maximumFractionDigits: 0 }).format(value);
};

const getPnlClass = (pnl) => {
  if (pnl > 0) return 'text-success';
  if (pnl < 0) return 'text-danger';
  return '';
};

const getKpiClass = (value, type) => {
  const val = parseFloat(value);
  if (type === 'wr') {
    if (val >= 0.3) return 'text-success';
    if (val < 0.25) return 'text-danger';
    return 'text-warning';
  }
  if (type === 'rr') {
    if (val >= 2.0) return 'text-success';
    if (val < 1.5) return 'text-danger';
    return 'text-warning';
  }
  return '';
};
</script>

<style>
/* --- New Styles for Features --- */
.report-meta {
  grid-column: 1 / -1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background-color: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}
.meta-item {
  color: #4b5563;
}
.meta-item span {
  margin-right: 0.5rem;
}
.meta-item strong {
  color: #1f2937;
  font-weight: 600;
}
.file-selection-note {
  font-size: 0.8rem;
  color: #6b7280;
  margin-top: 0.75rem;
  text-align: center;
}
.status-container {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}
.server-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #6b7280;
}
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #ef4444; /* Default to offline */
}
.status-dot.online {
  background-color: #22c55e;
}
.status-text strong {
  font-weight: 600;
}
.summary-table .clickable-row {
  cursor: pointer;
  transition: background-color 0.2s ease;
}
.summary-table .clickable-row:hover {
  background-color: #f0f4f8;
}
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-content {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1);
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 1rem;
  margin-bottom: 1rem;
}
.modal-header h3 {
  margin: 0;
  font-size: 1.5rem;
}
.close-button {
  background: none;
  border: none;
  font-size: 2rem;
  line-height: 1;
  cursor: pointer;
  color: #9ca3af;
}
.modal-body {
  overflow-y: auto;
}
.details-table {
  width: 100%;
  border-collapse: collapse;
}
.details-table th,
.details-table td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}
.details-table th {
  font-weight: 600;
  background-color: #f9fafb;
}

.annual-summary-year-block {
  margin-top: 1rem; /* Add some space between yearly summary blocks */
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}

.annual-summary-year-block:first-of-type {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

/* --- Existing & Updated Styles --- */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}
.kpi-card {
  background-color: #ffffff;
  padding: 1rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  text-align: center;
}
.kpi-card h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}
.kpi-card p {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: #1f2937;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}
.card {
  background-color: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  overflow: hidden;
}
.card-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  background-color: #f9fafb;
}
.card-header h2, .card-header h3 {
  margin: 0;
  font-size: 1.125rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.step {
  background-color: #3b82f6;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 600;
}
.card-body {
  padding: 1.5rem;
}
.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
}
.status-item span {
  color: #4b5563;
}
.status-item strong {
  font-weight: 600;
}
.reason {
  font-size: 0.875rem;
  color: #6b7280;
  margin-top: 0.75rem;
}
.incentive-amount {
  font-size: 1.5rem;
  font-weight: bold;
  color: #16a34a;
  text-align: center;
  margin: 0.5rem 0;
}
.violations {
  margin-top: 1rem;
  background-color: #fef2f2;
  padding: 0.75rem;
  border-radius: 6px;
  border: 1px solid #fecaca;
}
.violations h5 {
  margin: 0 0 0.5rem 0;
  color: #b91c1c;
}
.violations ul {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.875rem;
  color: #991b1b;
}

.text-success { color: #16a34a; }
.text-danger { color: #dc2626; }
.text-warning { color: #f59e0b; }

.full-width-card {
  grid-column: 1 / -1;
}
.summary-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}
.summary-table th,
.summary-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}
.summary-table th {
  font-weight: 600;
  background-color: #f9fafb;
}
.summary-table th:nth-child(n+6), .summary-table td:nth-child(n+6) {
    text-align: center;
}
.summary-table tbody tr:last-child td {
  border-bottom: none;
}

/* --- Base Layout & Form Styles --- */
:root {
  --bg-color: #f3f4f6;
  --text-color: #1f2937;
  --header-bg: #ffffff;
  --card-bg: #ffffff;
  --border-color: #e5e7eb;
}
body {
  font-family: 'Inter', sans-serif;
  background-color: var(--bg-color);
  color: var(--text-color);
  margin: 0;
}
main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem 2rem;
}
.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: var(--header-bg);
  border-bottom: 1px solid var(--border-color);
  margin: -1rem -2rem 2rem -2rem;
  position: sticky;
  top: 0;
  z-index: 999;
}
header h1 {
  font-size: 1.5rem;
  font-weight: 600;
}
.container {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 2rem;
  align-items: flex-start;
}
.form-section {
  position: sticky;
  top: 100px; /* Adjust based on header height */
}
.form-group {
  margin-bottom: 1rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  font-size: 0.875rem;
}
.form-group input, .form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  box-sizing: border-box;
}
.form-group input[type="file"] {
  padding: 0.5rem;
}
.analyze-button {
  width: 100%;
  padding: 0.875rem;
  background-color: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}
.analyze-button:hover {
  background-color: #1d4ed8;
}
.analyze-button:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
}
button[type="submit"] {
  width: 100%;
  padding: 0.875rem;
  background-color: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}
button[type="submit"]:hover {
  background-color: #1d4ed8;
}
button:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
}
.error-box, .loading-box, .placeholder-box {
  padding: 2rem;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  text-align: center;
  color: #6b7280;
}
.error-box {
  background-color: #fef2f2;
  border-color: #fca5a5;
  color: #991b1b;
}
</style>