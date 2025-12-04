<template>
  <main>
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
      <!-- Left side: Input Form -->
      <div class="form-section">
        <form @submit.prevent="runAudit" id="audit-form">
          <div class="card">
            <div class="card-header">
              <h2><span class="step">1</span> {{ $t('form.paramsTitle') }}</h2>
            </div>
            <div class="card-body">
              <div class="form-group">
                <label for="current_capital">{{ $t('form.currentCapital') }}</label>
                <input type="number" id="current_capital" v-model.number="params.current_capital" placeholder="e.g., 185000" required>
              </div>
              <div class="form-group">
                <label for="monthly_start_capital">{{ $t('form.monthlyStartCapital') }}</label>
                <input type="number" id="monthly_start_capital" v-model.number="params.monthly_start_capital" placeholder="e.g., 173000" required>
              </div>
              <div class="form-group">
                <label for="current_scale">{{ $t('form.scale') }}</label>
                <select id="current_scale" v-model="params.current_scale" required>
                  <option value="S1">S1</option>
                  <option value="S2">S2</option>
                  <option value="S3">S3</option>
                  <option value="S4">S4</option>
                </select>
              </div>
            </div>
          </div>

          <div class="card">
            <div class="card-header">
              <h2><span class="step">2</span> {{ $t('form.uploadTitle') }}</h2>
            </div>
            <div class="card-body">
              <div class="form-group">
                <label for="file">{{ $t('form.transactionLog') }}</label>
                <input type="file" id="file" @change="handleFileUpload" accept=".csv,.xlsx,.xls" required>
              </div>
            </div>
          </div>

          <button type="submit" :disabled="loading">
            {{ loading ? $t('form.analyzing') : $t('form.runAudit') }}
          </button>
        </form>
      </div>

      <!-- Right side: Dashboard Display -->
      <div class="dashboard-section">
        <div v-if="error" class="error-box">
          <strong>{{ $t('error.title') }}</strong> {{ errorDisplay }}
        </div>
        <div v-if="loading" class="loading-box">
          <p>{{ $t('loading') }}</p>
        </div>

        <!-- Upgrade Criteria Definition Card -->
        <div v-if="upgradeCriteria" class="card-grid">
            <div class="card full-width-card">
              <div class="card-header">
                <h3>{{ $t('dashboard.upgradeCriteria.title') }}</h3>
              </div>
              <div class="card-body">
                <table class="summary-table">
                  <thead>
                    <tr>
                      <th>{{ $t('dashboard.upgradeCriteria.scale') }}</th>
                      <th>{{ $t('dashboard.upgradeCriteria.nextScale') }}</th>
                      <th>{{ $t('dashboard.upgradeCriteria.capital') }}</th>
                      <th>{{ $t('dashboard.upgradeCriteria.rr') }}</th>
                      <th>{{ $t('dashboard.upgradeCriteria.wr') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(criteria, scale) in upgradeCriteria" :key="scale">
                      <td><strong>{{ scale }}</strong></td>
                      <td>{{ criteria.next_scale }}</td>
                      <td>≥ {{ formatCurrency(criteria.capital_key) }}</td>
                      <td>≥ {{ criteria.rr_key }}</td>
                      <td>≥ {{ criteria.wr_key * 100 }}%</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
        </div>
        
        <div v-if="report" id="report-dashboard">
          <!-- KPI Metrics Row -->
          <div class="kpi-grid">
            <div class="kpi-card">
              <h4>{{ $t('dashboard.kpi.winRate') }}</h4>
              <p :class="getKpiClass(report.kpi_metrics.win_rate, 'wr')">{{ report.kpi_metrics.win_rate }}</p>
            </div>
            <div class="kpi-card">
              <h4>{{ $t('dashboard.kpi.rr') }}</h4>
              <p :class="getKpiClass(report.kpi_metrics.risk_reward_ratio, 'rr')">{{ report.kpi_metrics.risk_reward_ratio }}</p>
            </div>
            <div class="kpi-card">
              <h4>{{ $t('dashboard.kpi.pnl') }}</h4>
              <p :class="getPnlClass(report.account_status.monthly_pnl)">{{ formatCurrency(report.account_status.monthly_pnl) }}</p>
            </div>
          </div>

          <!-- Other Cards -->
          <div class="card-grid">
            <!-- Account Status -->
            <div class="card">
              <div class="card-header"><h3>{{ $t('dashboard.accountStatus.title') }}</h3></div>
              <div class="card-body">
                <div class="status-item"><span>{{ $t('dashboard.accountStatus.currentScale') }}</span> <strong>{{ report.account_status.scale }}</strong></div>
                <div class="status-item"><span>{{ $t('dashboard.accountStatus.balance') }}</span> <strong>{{ formatCurrency(report.account_status.balance) }}</strong></div>
              </div>
            </div>
            <!-- Safety Checks -->
            <div class="card">
              <div class="card-header"><h3>{{ $t('dashboard.safetyChecks.title') }}</h3></div>
              <div class="card-body">
                <div class="status-item">
                  <span>{{ $t('dashboard.safetyChecks.dailyStop') }}</span>
                  <strong :class="report.safety_checks.daily_stop_violated ? 'text-danger' : 'text-success'">
                    {{ report.safety_checks.daily_stop_violated ? $t('dashboard.safetyChecks.violations.violated') : $t('dashboard.safetyChecks.violations.safe') }}
                  </strong>
                </div>
                <div class="status-item">
                  <span>{{ $t('dashboard.safetyChecks.monthlyBreaker') }}</span>
                  <strong :class="report.safety_checks.monthly_circuit_breaker === 'BREACHED' ? 'text-danger' : 'text-success'">
                    {{ report.safety_checks.monthly_circuit_breaker === 'BREACHED' ? $t('dashboard.safetyChecks.violations.breached') : $t('dashboard.safetyChecks.violations.safe') }}
                  </strong>
                </div>
                 <div v-if="report.safety_checks.night_session_violations.length > 0" class="violations">
                  <h5>{{ $t('dashboard.safetyChecks.violations.title') }}</h5>
                  <ul>
                    <li v-for="(v, i) in report.safety_checks.night_session_violations" :key="i">
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
                  <strong :class="report.evaluation.upgrade_eligible ? 'text-success' : 'text-warning'">
                    {{ report.evaluation.upgrade_eligible ? $t('dashboard.evaluation.yes') : $t('dashboard.evaluation.no') }}
                  </strong>
                </div>
                <p class="reason"><strong>{{ $t('dashboard.evaluation.reason') }}</strong> {{ report.evaluation.reason }}</p>
                <hr>
                <div class="status-item">
                  <span>{{ $t('dashboard.evaluation.incentive') }}</span>
                   <strong :class="report.evaluation.happiness_incentive.eligible ? 'text-success' : 'text-warning'">
                     {{ report.evaluation.happiness_incentive.eligible ? $t('dashboard.evaluation.eligible') : $t('dashboard.evaluation.notEligible') }}
                   </strong>
                </div>
                <div v-if="report.evaluation.happiness_incentive.eligible">
                  <p class="incentive-amount">{{ formatCurrency(report.evaluation.happiness_incentive.amount) }}</p>
                  <p class="reason">{{ report.evaluation.happiness_incentive.distribution }}</p>
                </div>
                 <div v-else>
                  <p class="reason">{{ report.evaluation.happiness_incentive.status }}</p>
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
                      <th>風險檢查</th>
                      <th>評估</th>
                      <th>激勵</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="summary in report.monthly_summary" :key="summary.month" @click="showMonthDetails(summary.month)" class="clickable-row">
                      <td>{{ summary.month }}</td>
                      <td :class="getPnlClass(summary.total_pnl)">{{ formatCurrency(summary.total_pnl) }}</td>
                      <td>{{ summary.win_rate }}</td>
                      <td>{{ summary.risk_reward_ratio }}</td>
                      <td>{{ summary.trade_count }}</td>
                      <td>
                        <span :class="summary.risk_check.monthly_circuit_breaker === 'BREACHED' || summary.risk_check.daily_stop_violated ? 'text-danger' : 'text-success'">
                          {{ summary.risk_check.monthly_circuit_breaker === 'BREACHED' || summary.risk_check.daily_stop_violated ? '違規' : '安全' }}
                        </span>
                      </td>
                      <td>
                        <span :class="summary.evaluation.upgrade_eligible ? 'text-success' : 'text-warning'">
                          {{ summary.evaluation.upgrade_eligible ? '合格' : '不合格' }}
                        </span>
                      </td>
                      <td>
                        <span :class="summary.incentive.eligible ? 'text-success' : (summary.incentive.status === '獲利保留補考' ? 'text-warning' : '')">
                          {{ summary.incentive.eligible ? formatCurrency(summary.incentive.amount) : summary.incentive.status }}
                        </span>
                      </td>
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

// --- Remote Logger ---
const logToServer = async (level, message, context = {}) => {
  try {
    await fetch('http://localhost:8000/api/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level, message, context }),
    });
  } catch (e) {
    console.error("CRITICAL: Failed to send log to server:", e); // Fallback for when logger itself fails
  }
};

const logger = {
  info: (message, context) => logToServer('info', message, context),
  warn: (message, context) => logToServer('warn', message, context),
  error: (message, context) => logToServer('error', message, context),
};

// --- Refs and State ---
const params = ref({
  current_capital: null,
  monthly_start_capital: null,
  current_scale: 'S1',
});
const file = ref(null);
const report = ref(null);
const loading = ref(false);
const error = ref(null);
const errorMessage = ref('');
const serverStatus = ref('offline'); // offline | online
const selectedMonth = ref(null); // e.g., '2025-07'
const upgradeCriteria = ref(null);

// --- Computed Properties ---
const errorDisplay = computed(() => {
  if (error.value === 'error.failed') {
    return t('error.failed', { message: errorMessage.value });
  }
  return error.value ? t(error.value) : '';
});

const selectedMonthTrades = computed(() => {
  if (!selectedMonth.value || !report.value || !report.value.monthly_trades) {
    return [];
  }
  return report.value.monthly_trades[selectedMonth.value] || [];
});


// --- Lifecycle Hooks ---
onMounted(() => {
  logger.info('Frontend application mounted and ready.');
  checkServerStatus();
  setInterval(checkServerStatus, 10000); // Poll every 10 seconds
  fetchUpgradeCriteria();
});

// --- Methods ---
const fetchUpgradeCriteria = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/upgrade-criteria');
    if (response.ok) {
      upgradeCriteria.value = await response.json();
      logger.info('Successfully fetched upgrade criteria.');
    } else {
      throw new Error('Failed to fetch upgrade criteria');
    }
  } catch (e) {
    logger.error('Could not fetch upgrade criteria.', { error: e.message });
  }
};

const checkServerStatus = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/status');
    serverStatus.value = response.ok ? 'online' : 'offline';
  } catch (e) {
    serverStatus.value = 'offline';
  }
};

const handleFileUpload = (event) => {
  const selectedFile = event.target.files[0];
  if (selectedFile) {
    file.value = selectedFile;
    logger.info(`File selected for upload: ${selectedFile.name}`, { size: selectedFile.size, type: selectedFile.type });
  }
};

const runAudit = async () => {
  if (!file.value) {
    error.value = 'error.noFile';
    logger.warn('Audit submission failed: No file selected.');
    return;
  }
  loading.value = true;
  error.value = null;
  errorMessage.value = '';
  report.value = null;
  selectedMonth.value = null; // Reset details view on new audit

  const formData = new FormData();
  formData.append('current_capital', params.value.current_capital);
  formData.append('monthly_start_capital', params.value.monthly_start_capital);
  formData.append('current_scale', params.value.current_scale);
  formData.append('file', file.value);
  
  logger.info('Starting audit run.', { 
    params: { 
      current_capital: params.value.current_capital, 
      monthly_start_capital: params.value.monthly_start_capital,
      current_scale: params.value.current_scale 
    },
    fileName: file.value.name 
  });

  try {
    const response = await fetch('http://localhost:8000/api/audit', {
      method: 'POST',
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP error! status: ${response.status}`);
    }
    report.value = data;
    logger.info('Audit API call successful. Report data received.');
  } catch (e) {
    error.value = 'error.failed';
    errorMessage.value = e.message;
    logger.error('Audit API call failed.', { error: e.message, stack: e.stack });
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

/* --- Existing Styles --- */
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
.summary-table tbody tr:last-child td {
  border-bottom: none;
}
</style>