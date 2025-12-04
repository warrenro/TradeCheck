
<template>
  <main>
    <div class="header-container">
      <header>
        <h1>{{ $t('header.title') }}</h1>
      </header>
      <div class="lang-switcher">
        <select v-model="$i18n.locale">
          <option value="zh-TW">繁體中文</option>
          <option value="en">English</option>
        </select>
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
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="summary in report.monthly_summary" :key="summary.month">
                      <td>{{ summary.month }}</td>
                      <td :class="getPnlClass(summary.total_pnl)">{{ formatCurrency(summary.total_pnl) }}</td>
                      <td>{{ summary.win_rate }}</td>
                      <td>{{ summary.risk_reward_ratio }}</td>
                      <td>{{ summary.trade_count }}</td>
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
  </main>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const params = ref({
  current_capital: null,
  monthly_start_capital: null,
  current_scale: 'S1',
});

const file = ref(null);
const report = ref(null);
const loading = ref(false);
const error = ref(null); // Stores the error message key or raw message
const errorMessage = ref(''); // Stores the dynamic part of the error message

const errorDisplay = computed(() => {
  if (error.value === 'error.failed') {
    return t('error.failed', { message: errorMessage.value });
  }
  return error.value ? t(error.value) : '';
});

const handleFileUpload = (event) => {
  file.value = event.target.files[0];
};

const runAudit = async () => {
  if (!file.value) {
    error.value = 'error.noFile';
    return;
  }
  loading.value = true;
  error.value = null;
  errorMessage.value = '';
  report.value = null;

  const formData = new FormData();
  formData.append('current_capital', params.value.current_capital);
  formData.append('monthly_start_capital', params.value.monthly_start_capital);
  formData.append('current_scale', params.value.current_scale);
  formData.append('file', file.value);

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
  } catch (e) {
    error.value = 'error.failed';
    errorMessage.value = e.message;
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const formatCurrency = (value) => {
  if (value === null || value === undefined) return 'N/A';
  // Use a neutral locale for formatting, as this is about currency, not language
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
/* Add styles for the new elements */
.full-width-card {
  grid-column: 1 / -1; /* Span across all columns */
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

