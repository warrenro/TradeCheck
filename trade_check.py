
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Tuple
import os
import glob
import logging
import configparser

# --- Logging Setup ---
# Configure logger to write to a file and the console
log_file = os.path.join(os.path.dirname(__file__), 'trade_audit.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Constants based on spec.md ---

# 8. Appendix: Point values for products
POINT_VALUES = {
    "小型臺指": 50,
    "小型台指": 50,
    "小臺": 50,
    "微型臺指": 10,
    "微型台指": 10,
    "臺指": 200,
    "台指": 200,
}

# 2.1 Trading DNA Diagnosis Rules
TRADING_DNA_RULES = {
    "NOISE_ZONE_THRESHOLD": 40,
    "NOISE_ZONE_TRADE_PERCENT_THRESHOLD": 0.8,
    "TREND_ZONE_WIN_RATE_THRESHOLD": 0.3,
    "MONTHLY_POINT_TARGET": 30,
}

# 2.4 SOP Risk Stress Test Rules
SOP_RISK_STRESS_TEST = {
    "MAX_EXPOSURE_POINTS": 1500,
    "RISK_RATIO_THRESHOLD": 0.15,
    "SOP_B_SCALE_FACTOR": 0.2,
}

# 2.2.3 Strategy Circuit Breaker
STRATEGY_CIRCUIT_BREAKER_THRESHOLD = 10

# 2.3.1 Quarterly Cost Deduction
QUARTERLY_COST = 25000
QUARTERLY_MONTHS = [3, 6, 9, 12]


# Appendix: Upgrade Criteria
UPGRADE_CRITERIA = {
    "S1": {"next_scale": "S2", "capital_key": 200000, "rr_key": 1.5, "wr_key": 0.25},
    "S2": {"next_scale": "S3", "capital_key": 400000, "rr_key": 2.0, "wr_key": 0.30},
    "S3": {"next_scale": "S4", "capital_key": 600000, "rr_key": 2.0, "wr_key": 0.33},
    "S4": {"next_scale": "S5", "capital_key": 800000, "rr_key": 2.5, "wr_key": 0.35},
}

# 2.2.4 Night Session Hedging Window
NIGHT_SESSION_VIOLATIONS = [
    {"name": "Night Session Hedging 1", "start": "21:15:00", "end": "21:45:00"},
    {"name": "Night Session Hedging 2", "start": "01:45:00", "end": "02:15:00"},
]

# (Legacy) 4.3.A. The Moat Rule Period 
# This rule seems to be replaced or not mentioned in the new spec, keeping for legacy purposes.
MOAT_RULE_START = datetime.strptime("2026-01-01", "%Y-%m-%d")
MOAT_RULE_END = datetime.strptime("2026-08-31", "%Y-%m-%d")

def find_latest_trade_file(directory: str) -> str:
    """Finds the most recently modified trade file (.csv or .xlsx) in a directory."""
    logger.info(f"Searching for trade files in directory: {directory}")
    list_of_files = glob.glob(os.path.join(directory, '*.csv')) + glob.glob(os.path.join(directory, '*.xlsx'))
    if not list_of_files:
        logger.error(f"No trade files (.csv, .xlsx) found in directory: {directory}")
        raise FileNotFoundError(f"No trade files (.csv, .xlsx) found in the directory: {directory}")
    
    latest_file = max(list_of_files, key=os.path.getmtime)
    logger.info(f"Found latest trade file: {latest_file}")
    return latest_file

class TradeAuditor:
    """
    Automated audit system for D-Pro Protocol V7.3.
    """
    def __init__(self, current_capital: float, monthly_start_capital: float, current_scale: str, operation_contracts: int):
        logger.info(f"Initializing TradeAuditor for scale {current_scale} with capital {current_capital}.")
        if current_scale not in UPGRADE_CRITERIA:
            log_msg = f"Invalid scale '{current_scale}'. Must be one of {list(UPGRADE_CRITERIA.keys())}"
            logger.error(log_msg)
            raise ValueError(log_msg)
            
        self.current_capital = current_capital
        self.monthly_start_capital = monthly_start_capital
        self.current_scale = current_scale
        self.operation_contracts = operation_contracts
        self.report_date = datetime.now().strftime("%Y-%m-%d")

    def load_transactions(self, file_path: str) -> pd.DataFrame:
        """Loads transaction data from a CSV or Excel file."""
        logger.info(f"Loading transactions from file: {file_path}")
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, thousands=',')
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Unsupported file type. Please use CSV or Excel.")

            # --- Data Validation and Transformation ---
            required_columns = {'成交時間', '買賣別', '平倉損益淨額', '口數', '商品名稱'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise ValueError(f"Missing required columns: {missing}. Found: {df.columns}.")

            column_mapping = {
                '成交時間': 'trade_time',
                '買賣別': 'action',
                '平倉損益淨額': 'net_pnl',
                '口數': 'contracts',
                '商品名稱': 'product_name'
            }
            df.rename(columns=column_mapping, inplace=True)

            df['trade_time'] = pd.to_datetime(df['trade_time'])
            df['net_pnl'] = df['net_pnl'].astype(str).str.replace(',', '').astype(float)
            df['contracts'] = df['contracts'].astype(int)
            df['product_name'] = df['product_name'].str.strip()

            logger.info(f"Successfully loaded and processed {len(df)} transactions.")
            return df
        except FileNotFoundError:
            logger.error(f"Transaction file not found at path: {file_path}", exc_info=True)
            raise
        except ValueError as e:
            logger.error(f"Error processing transaction file: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during transaction loading: {e}", exc_info=True)
            raise

    def _add_trade_points_column(self, trades: pd.DataFrame) -> pd.DataFrame:
        """Calculates and adds the 'points' column to the trades DataFrame."""
        logger.info("Calculating trade points for DNA diagnosis.")
        
        def calculate_points(row):
            product_name = row['product_name']
            # Find the corresponding point value, trying to match parts of the name
            point_value = next((POINT_VALUES[key] for key in POINT_VALUES if key in product_name), None)

            if point_value is None:
                logger.warning(f"No point value found for product '{product_name}'. Cannot calculate points for this trade.")
                return None
            
            if row['contracts'] == 0:
                logger.warning(f"Trade has 0 contracts. Cannot calculate points. PnL: {row['net_pnl']}")
                return 0

            return row['net_pnl'] / (row['contracts'] * point_value)

        trades['points'] = trades.apply(calculate_points, axis=1)
        logger.info("Successfully calculated and added 'points' column.")
        return trades

    def _calculate_kpis(self, trades: pd.DataFrame) -> Tuple[float, float, float]:
        """Calculates Win Rate (WR) and Risk/Reward Ratio (RR)."""
        if trades.empty:
            logger.warning("KPI calculation attempted on an empty DataFrame.")
            return 0.0, 0.0, 0.0

        total_trades = len(trades)
        winning_trades = trades[trades['net_pnl'] > 0]
        losing_trades = trades[trades['net_pnl'] < 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        avg_win = winning_trades['net_pnl'].mean() if not winning_trades.empty else 0
        avg_loss = abs(losing_trades['net_pnl'].mean()) if not losing_trades.empty else 0
        risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
        monthly_pnl = trades['net_pnl'].sum()

        logger.info(f"KPIs calculated: WR={win_rate:.2%}, RR={risk_reward_ratio:.2f}, PnL={monthly_pnl:,.2f}")
        return win_rate, risk_reward_ratio, monthly_pnl

    def _run_trading_dna_diagnosis(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Runs the Trading DNA Diagnosis based on trade points."""
        logger.info("Running Trading DNA Diagnosis.")
        if 'points' not in trades.columns or trades['points'].isnull().all():
            logger.warning("'points' column not available or all null. Skipping DNA diagnosis.")
            return {}

        total_trades = len(trades)
        total_points = trades['points'].sum()

        # --- Noise Zone ---
        noise_threshold = TRADING_DNA_RULES['NOISE_ZONE_THRESHOLD']
        noise_trades = trades[abs(trades['points']) <= noise_threshold]
        noise_count = len(noise_trades)
        noise_pnl = noise_trades['net_pnl'].sum()
        noise_win_rate = (noise_trades['net_pnl'] > 0).sum() / noise_count if noise_count > 0 else 0
        
        noise_verdict = "N/A"
        if noise_count > 0:
            trade_ratio = noise_count / total_trades
            if trade_ratio > TRADING_DNA_RULES['NOISE_ZONE_TRADE_PERCENT_THRESHOLD'] and noise_pnl < 0:
                noise_verdict = "陷入泥淖 (Stuck in the Mud)"
            else:
                noise_verdict = "防守得宜 (Good Defense)"

        # --- Trend Zone ---
        trend_trades = trades[abs(trades['points']) > noise_threshold]
        trend_count = len(trend_trades)
        trend_pnl = trend_trades['net_pnl'].sum()
        trend_win_rate = (trend_trades['net_pnl'] > 0).sum() / trend_count if trend_count > 0 else 0

        trend_verdict = "N/A"
        if trend_count > 0:
            if trend_win_rate >= TRADING_DNA_RULES['TREND_ZONE_WIN_RATE_THRESHOLD']:
                trend_verdict = "獲利核心 (Profit Core)"
            else:
                trend_verdict = "錯失行情 (Missed Trends)"

        return {
            "monthly_point_target": TRADING_DNA_RULES['MONTHLY_POINT_TARGET'],
            "total_points_achieved": round(total_points, 2),
            "noise_zone": {
                "trade_count": noise_count,
                "win_rate": f"{noise_win_rate:.2%}",
                "total_pnl": round(noise_pnl, 2),
                "verdict": noise_verdict
            },
            "trend_zone": {
                "trade_count": trend_count,
                "win_rate": f"{trend_win_rate:.2%}",
                "total_pnl": round(trend_pnl, 2),
                "verdict": trend_verdict
            }
        }

    def _run_sop_risk_stress_test(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Runs the SOP Risk Stress Test based on D-Pro V2.99."""
        logger.info("Running SOP Risk Stress Test.")
        
        # Assumption: The primary instrument for risk calculation is '小型台指'.
        # A more robust implementation might determine this from the trade data itself.
        primary_point_value = POINT_VALUES.get("小型台指", 50)
        
        max_points = SOP_RISK_STRESS_TEST['MAX_EXPOSURE_POINTS']
        
        # SOP-A Risk
        sop_a_risk = max_points * primary_point_value * 1  # 1 contract
        
        # SOP-B Risk
        sop_b_contracts = self.operation_contracts * SOP_RISK_STRESS_TEST['SOP_B_SCALE_FACTOR']
        sop_b_risk = max_points * primary_point_value * sop_b_contracts
        
        # Risk Ratio Calculation
        risk_ratio = sop_b_risk / self.current_capital if self.current_capital > 0 else float('inf')
        
        warning = None
        if risk_ratio > SOP_RISK_STRESS_TEST['RISK_RATIO_THRESHOLD']:
            warning = "高風險警告：建議降級或切換至 SOP-A (High Risk Warning: Consider downgrade or switch to SOP-A)"
            logger.warning(f"SOP Risk Stress Test: {warning} (Risk Ratio: {risk_ratio:.2%})")

        return {
            "sop_a_potential_risk": round(sop_a_risk, 2),
            "sop_b_potential_risk": round(sop_b_risk, 2),
            "risk_ratio": f"{risk_ratio:.2%}",
            "warning": warning
        }


    def _check_safety_valves(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """4.1.B & 2.2.3: Checks for daily stop, monthly capital, and strategy circuit breakers."""
        logger.info("Checking safety valves: Daily Stop, Monthly Capital, and Strategy Circuit Breaker.")
        
        # Daily Stop (Intraday Risk Control)
        daily_loss_counts = trades[trades['net_pnl'] < 0].groupby(trades['trade_time'].dt.date).size()
        daily_stop_violation_days = (daily_loss_counts > 3).sum()
        daily_stop_triggered = daily_stop_violation_days > 0
        if daily_stop_triggered:
            logger.warning(f"Daily Stop violation detected on {daily_stop_violation_days} day(s).")

        # Strategy Circuit Breaker (Monthly)
        strategy_circuit_breaker_triggered = daily_stop_violation_days > STRATEGY_CIRCUIT_BREAKER_THRESHOLD
        if strategy_circuit_breaker_triggered:
            logger.warning(f"Strategy Circuit Breaker triggered. Daily stop violations ({daily_stop_violation_days}) exceeded threshold ({STRATEGY_CIRCUIT_BREAKER_THRESHOLD}).")

        # Capital Circuit Breaker (Monthly)
        monthly_pnl = trades['net_pnl'].sum()
        monthly_loss_threshold = - (self.monthly_start_capital * 0.15)
        capital_circuit_breaker = "BREACHED" if monthly_pnl <= monthly_loss_threshold else "SAFE"
        if capital_circuit_breaker == "BREACHED":
            logger.warning(f"Monthly Capital Circuit Breaker breached. PnL {monthly_pnl:,.2f} <= Threshold {monthly_loss_threshold:,.2f}")
        
        return {
            "daily_stop_violated_days": int(daily_stop_violation_days),
            "strategy_circuit_breaker_triggered": bool(strategy_circuit_breaker_triggered),
            "capital_circuit_breaker_status": capital_circuit_breaker,
        }

    def _check_night_session(self, trades: pd.DataFrame) -> List[Dict[str, str]]:
        """2.2.4: Checks for opening new positions during restricted night session windows."""
        logger.info("Checking for night session violations (opening trades only).")
        violations = []
        # Filter for trades that are considered 'opening' a new position
        opening_trades = trades[trades['action'].isin(['買進', '賣出'])]

        for _, trade in opening_trades.iterrows():
            trade_time = trade['trade_time'].time()
            for window in NIGHT_SESSION_VIOLATIONS:
                start = datetime.strptime(window['start'], '%H:%M:%S').time()
                end = datetime.strptime(window['end'], '%H:%M:%S').time()
                if start <= trade_time <= end:
                    violation_details = {
                        "rule": window['name'],
                        "violation_time": trade['trade_time'].strftime('%Y-%m-%d %H:%M:%S'),
                        "action": trade['action']
                    }
                    violations.append(violation_details)
                    logger.warning(f"Night session violation found: {violation_details}")
        return violations

    def _evaluate_capital_management(self, win_rate: float, risk_reward_ratio: float, trade_month: int) -> Dict[str, Any]:
        """2.3: Evaluates upgrade eligibility, including quarterly cost deduction."""
        logger.info(f"Evaluating capital management for scale {self.current_scale}.")
        criteria = UPGRADE_CRITERIA.get(self.current_scale, {})
        upgrade_eligible = False
        reason = "No further upgrade path from this scale."
        
        adjusted_capital = self.current_capital
        cost_deducted = 0

        # 2.3.1 Quarterly Cost Deduction ('中哥費')
        if trade_month in QUARTERLY_MONTHS:
            adjusted_capital -= QUARTERLY_COST
            cost_deducted = QUARTERLY_COST
            logger.info(f"Quarterly cost of {QUARTERLY_COST} deducted for month {trade_month}. Adjusted capital: {adjusted_capital:,.0f}")

        if criteria:
            capital_ok = adjusted_capital >= criteria['capital_key']
            perf_ok = risk_reward_ratio >= criteria['rr_key'] and win_rate >= criteria['wr_key']

            if capital_ok and perf_ok:
                upgrade_eligible = True
                reason = f"All conditions met for {criteria['next_scale']}."
                logger.info(f"Account is eligible for upgrade to {criteria['next_scale']}.")
            else:
                reasons = []
                if not capital_ok:
                    reasons.append(f"Capital Key not met ({adjusted_capital:,.0f} < {criteria['capital_key']:,.0f})")
                if not perf_ok:
                    reasons.append(f"Performance Key not met (RR: {risk_reward_ratio:.2f}, WR: {win_rate:.2%})")
                reason = ", ".join(reasons)
                logger.info(f"Account not eligible for upgrade. Reason: {reason}")

        return {
            "upgrade_eligible": upgrade_eligible,
            "reason": reason,
            "current_criteria": criteria if criteria else None,
            "capital_adjustment": {
                "quarterly_cost_deducted": cost_deducted,
                "capital_before_adjustment": self.current_capital,
                "capital_after_adjustment": adjusted_capital
            }
        }

    def _calculate_happiness_incentive(self, monthly_pnl: float, win_rate: float, risk_reward_ratio: float) -> Dict[str, Any]:
        """2.3.2: Calculates the Happiness Incentive based on monthly performance."""
        logger.info("Calculating Happiness Incentive.")
        
        # Happiness Incentive
        kpi_criteria = UPGRADE_CRITERIA[self.current_scale]
        kpi_met = risk_reward_ratio >= kpi_criteria['rr_key'] and win_rate >= kpi_criteria['wr_key']

        if monthly_pnl > 0 and kpi_met:
            incentive_amount = monthly_pnl * 0.10
            result = {
                "eligible": True,
                "amount": int(round(incentive_amount)),
                "status": "KPIs met and profitable."
            }
            logger.info(f"Happiness Incentive is eligible. Amount: {result['amount']}.")
            return result
        elif monthly_pnl > 0 and not kpi_met:
            logger.info("Happiness Incentive not eligible: KPI not met, profit reserved.")
            return {"eligible": False, "amount": 0, "status": "Profitable, but KPIs not met. Profit reserved."}
        else:
            logger.info("Happiness Incentive not eligible: No profit this month.")
            return {"eligible": False, "amount": 0, "status": "Not profitable this month."}

    def calculate_monthly_summary(self, trades: pd.DataFrame) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """
        Groups all trades by month and calculates summary statistics and detailed trades.
        Returns a tuple of (summary_list, monthly_trades_dict).
        """
        if trades.empty:
            return [], {}
        
        logger.info("Calculating historical monthly summary and trade details.")
        trades['trade_time'] = pd.to_datetime(trades['trade_time'])

        monthly_groups = trades.groupby(pd.Grouper(key='trade_time', freq='M'))
        
        summary_list = []
        monthly_trades_dict = {}

        for month_ts, group in monthly_groups:
            if group.empty:
                continue
            
            month_str = month_ts.strftime('%Y-%m')
            trade_month = month_ts.month
            
            # --- Monthly Calculations & Evaluations ---
            win_rate, rr, pnl = self._calculate_kpis(group)
            risk_check = self._check_safety_valves(group)
            # Note: Historical evaluations use the *current* capital context, which might not be accurate for past months.
            evaluation = self._evaluate_capital_management(win_rate, rr, trade_month)
            incentive = self._calculate_happiness_incentive(pnl, win_rate, rr)
            
            summary = {
                "month": month_str,
                "total_pnl": float(round(pnl, 2)),
                "win_rate": f"{win_rate:.2%}",
                "risk_reward_ratio": f"{rr:.2f}",
                "trade_count": len(group),
                "risk_audit": risk_check,
                "capital_assessment": evaluation,
                "happiness_incentive": incentive,
            }
            summary_list.append(summary)
            
            # Prepare detailed trades for this month, ensuring 'points' is included
            group_copy = group.copy()
            group_copy['trade_time'] = group_copy['trade_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
            # Ensure 'points' column is rounded for clean JSON output
            if 'points' in group_copy.columns:
                group_copy['points'] = group_copy['points'].round(2)
            monthly_trades_dict[month_str] = group_copy.to_dict('records')

        logger.info(f"Generated summary for {len(summary_list)} months.")
        # Sort summary list by month descending
        sorted_summary = sorted(summary_list, key=lambda x: x['month'], reverse=True)
        return sorted_summary, monthly_trades_dict

    def run_audit(self, file_path: str) -> Dict[str, Any]:
        """Executes the full audit process and returns a JSON report."""
        logger.info(f"--- Starting Full Audit for file: {file_path} ---")
        try:
            trades = self.load_transactions(file_path)
            trades = self._add_trade_points_column(trades)

            # Determine the month for the audit from the latest trade
            latest_trade_month = trades['trade_time'].max().month
            
            # --- Perform All Calculations & Audits ---
            win_rate, risk_reward_ratio, total_pnl = self._calculate_kpis(trades)
            risk_audit = self._check_safety_valves(trades)
            risk_audit['night_session_violations'] = self._check_night_session(trades)
            
            dna_diagnosis = self._run_trading_dna_diagnosis(trades)
            stress_test = self._run_sop_risk_stress_test(trades)
            
            capital_assessment = self._evaluate_capital_management(win_rate, risk_reward_ratio, latest_trade_month)
            capital_assessment['happiness_incentive'] = self._calculate_happiness_incentive(total_pnl, win_rate, risk_reward_ratio)

            # --- Historical Summary ---
            monthly_summary, monthly_trades = self.calculate_monthly_summary(trades)

            # --- Construct Final Report ---
            report = {
                "report_date": self.report_date,
                "account_summary": {
                    "scale": self.current_scale, 
                    "current_balance": self.current_capital, 
                    "monthly_pnl": float(round(total_pnl, 2)),
                    "kpi_metrics": {
                        "win_rate": f"{win_rate:.2%}", 
                        "risk_reward_ratio": f"{risk_reward_ratio:.2f}"
                    }
                },
                "risk_audit": risk_audit,
                "trading_dna_diagnosis": dna_diagnosis,
                "sop_risk_stress_test": stress_test,
                "capital_assessment": capital_assessment,
                "historical_summary": monthly_summary,
                "detailed_trades": monthly_trades,
                "static_rules": {
                    "upgrade_criteria": UPGRADE_CRITERIA,
                    "point_values": POINT_VALUES
                },
            }
            logger.info(f"--- Audit Completed Successfully ---")
            return report
        except Exception as e:
            logger.critical(f"A critical error occurred during the audit run: {e}", exc_info=True)
            raise

# --- Main Execution ---
if __name__ == '__main__':
    logger.info("="*50)
    logger.info("Executing TradeCheck Auditor as a standalone script.")
    logger.info("="*50)
    
    config = configparser.ConfigParser()
    config_file = 'config.ini'
    
    try:
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
            
        config.read(config_file)
        
        # --- Load Parameters from Config ---
        account_section = config['Account']
        current_capital = account_section.getfloat('current_capital')
        monthly_start_capital = account_section.getfloat('monthly_start_capital')
        current_scale = account_section.get('current_scale')
        operation_contracts = account_section.getint('operation_contracts')
        
        logger.info(f"Loaded parameters from {config_file}:")
        logger.info(f"  - Current Capital: {current_capital:,.0f}")
        logger.info(f"  - Monthly Start Capital: {monthly_start_capital:,.0f}")
        logger.info(f"  - Current Scale: {current_scale}")
        logger.info(f"  - Operation Contracts: {operation_contracts}")

        # --- Find Latest Trade File ---
        trade_data_directory = 'tradedata'
        latest_file_path = find_latest_trade_file(trade_data_directory)
        
        # --- Run Audit ---
        auditor = TradeAuditor(
            current_capital=current_capital,
            monthly_start_capital=monthly_start_capital,
            current_scale=current_scale,
            operation_contracts=operation_contracts
        )
        report = auditor.run_audit(latest_file_path)
        
        # --- Save Report ---
        output_filename = 'audit_report.json'
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Successfully generated audit report: '{output_filename}'")
        print(f"\nAudit complete. Report saved to '{output_filename}'.")

    except FileNotFoundError as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"Error: {e}")
    except (configparser.Error, KeyError) as e:
        logger.error(f"Error reading or parsing config file '{config_file}': {e}", exc_info=True)
        print(f"Error in '{config_file}': {e}")
    except Exception as e:
        logger.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}")
