**Title:** [BUG] 前端無法顯示審計報告 (Frontend Fails to Display Audit Report)

**Body:**

**Describe the bug**
The frontend does not display the audit report after a successful API call. The UI remains in the initial state, even though the backend returns the correct JSON data.

**Root Cause**
A typo was found in the data binding expression within the `TradeCheck/frontend/src/App.vue` file.

The code in the monthly summary table was trying to access `summary.incentive.amount` to display the happiness incentive amount. However, according to the data structure returned by the API, the correct path is `summary.happiness_incentive.amount`.

This incorrect data path caused a runtime rendering error in the Vue component, which prevented the entire report section from being displayed.

**File to modify:** `TradeCheck/frontend/src/App.vue`

**Incorrect Code:**
```vue
{{ summary.happiness_incentive.eligible ? formatCurrency(summary.incentive.amount) : summary.happiness_incentive.status }}
```

**Corrected Code:**
```vue
{{ summary.happiness_incentive.eligible ? formatCurrency(summary.happiness_incentive.amount) : summary.happiness_incentive.status }}
```

**Solution**
The data path in `App.vue` has been corrected. This resolves the rendering error and allows the audit report to be displayed correctly.
