
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Tuple
import os
import glob
import logging

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

# --- Constants based on Spec V7.3 ---

# 4.2.A. Double-Key Upgrade Criteria
UPGRADE_CRITERIA = {
    "S1": {"next_scale": "S2", "capital_key": 200000, "rr_key": 1.5, "wr_key": 0.25},
    "S2": {"next_scale": "S3", "capital_key": 400000, "rr_key": 2.0, "wr_key": 0.30},
    "S3": {"next_scale": "S4", "capital_key": 600000, "rr_key": 2.0, "wr_key": 0.33},
    "S4": {"next_scale": "S5", "capital_key": 800000, "rr_key": 2.5, "wr_key": 0.35},
}

# 4.1.A. Night Session Violation Time Windows
NIGHT_SESSION_VIOLATIONS = [
    {"name": "US Market Open", "start": "21:15:00", "end": "21:45:00"},
    {"name": "FOMC Announcement", "start": "01:45:00", "end": "02:15:00"},
]

# 4.3.A. The Moat Rule Period
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
    def __init__(self, current_capital: float, monthly_start_capital: float, current_scale: str):
        logger.info(f"Initializing TradeAuditor for scale {current_scale} with capital {current_capital}.")
        if current_scale not in UPGRADE_CRITERIA:
            log_msg = f"Invalid scale '{current_scale}'. Must be one of {list(UPGRADE_CRITERIA.keys())}"
            logger.error(log_msg)
            raise ValueError(log_msg)
            
        self.current_capital = current_capital
        self.monthly_start_capital = monthly_start_capital
        self.current_scale = current_scale
        self.report_date = datetime.now().strftime("%Y-%m-%d")

    def load_transactions(self, file_path: str) -> pd.DataFrame:
        """Loads transaction data from a CSV or Excel file."""
        logger.info(f"Loading transactions from file: {file_path}")
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Unsupported file type. Please use CSV or Excel.")

            # --- Data Validation and Transformation ---
            original_required_columns = {'成交時間', '買賣別', '平倉損益淨額'}
            if not original_required_columns.issubset(df.columns):
                raise ValueError(f"Missing required columns. Found: {df.columns}. Required: {original_required_columns}")

            column_mapping = {'成交時間': 'trade_time', '買賣別': 'action', '平倉損益淨額': 'net_pnl'}
            df.rename(columns=column_mapping, inplace=True)

            df['trade_time'] = pd.to_datetime(df['trade_time'])
            df['net_pnl'] = df['net_pnl'].astype(str).str.replace(',', '').astype(float)
            
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

    def _check_safety_valves(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """4.1.B: Checks for daily stop and monthly circuit breaker violations."""
        logger.info("Checking safety valves: Daily Stop and Monthly Circuit Breaker.")
        daily_loss_counts = trades[trades['net_pnl'] < 0].groupby(trades['trade_time'].dt.date).size()
        daily_stop_violated = (daily_loss_counts > 3).any()
        if daily_stop_violated:
            logger.warning("Daily Stop violation detected (more than 3 losing trades in a day).")

        monthly_pnl = trades['net_pnl'].sum()
        monthly_loss_threshold = - (self.monthly_start_capital * 0.15)
        monthly_circuit_breaker = "BREACHED" if monthly_pnl <= monthly_loss_threshold else "SAFE"
        if monthly_circuit_breaker == "BREACHED":
            logger.warning(f"Monthly Circuit Breaker breached. PnL {monthly_pnl:,.2f} <= Threshold {monthly_loss_threshold:,.2f}")
        
        return {
            "daily_stop_violated": bool(daily_stop_violated),
            "monthly_circuit_breaker": monthly_circuit_breaker,
        }

    def _check_night_session(self, trades: pd.DataFrame) -> List[Dict[str, str]]:
        """4.1.A: Checks for trading during restricted night session windows."""
        logger.info("Checking for night session violations.")
        violations = []
        for _, trade in trades.iterrows():
            trade_time = trade['trade_time'].time()
            for window in NIGHT_SESSION_VIOLATIONS:
                start = datetime.strptime(window['start'], '%H:%M:%S').time()
                end = datetime.strptime(window['end'], '%H:%M:%S').time()
                if start <= trade_time <= end:
                    violation_details = {
                        "rule": window['name'],
                        "violation_time": trade['trade_time'].strftime('%Y-%m-%d %H:%M:%S')
                    }
                    violations.append(violation_details)
                    logger.warning(f"Night session violation found: {violation_details}")
        return violations

    def _evaluate_capital_management(self, win_rate: float, risk_reward_ratio: float) -> Dict[str, Any]:
        """4.2: Evaluates upgrade eligibility and demotion warnings."""
        logger.info(f"Evaluating capital management for scale {self.current_scale}.")
        criteria = UPGRADE_CRITERIA.get(self.current_scale, {})
        upgrade_eligible = False
        reason = "No further upgrade path from this scale."

        if criteria:
            capital_ok = self.current_capital >= criteria['capital_key']
            perf_ok = risk_reward_ratio >= criteria['rr_key'] and win_rate >= criteria['wr_key']

            if capital_ok and perf_ok:
                upgrade_eligible = True
                reason = f"All conditions met for {criteria['next_scale']}."
                logger.info(f"Account is eligible for upgrade to {criteria['next_scale']}.")
            else:
                reasons = []
                if not capital_ok:
                    reasons.append(f"Capital Key not met ({self.current_capital:,.0f} < {criteria['capital_key']:,.0f})")
                if not perf_ok:
                    reasons.append(f"Performance Key not met (RR: {risk_reward_ratio:.2f}, WR: {win_rate:.2%})")
                reason = ", ".join(reasons)
                logger.info(f"Account not eligible for upgrade. Reason: {reason}")

        return {
            "upgrade_eligible": upgrade_eligible,
            "reason": reason,
            "current_criteria": criteria if criteria else None,
        }

    def _evaluate_life_strategy(self, monthly_pnl: float, win_rate: float, risk_reward_ratio: float) -> Dict[str, Any]:
        """4.3: Checks Moat Rule and calculates Happiness Incentive."""
        logger.info("Evaluating life strategy (Moat Rule and Happiness Incentive).")
        # The Moat Rule
        is_moat_period = MOAT_RULE_START <= datetime.now() <= MOAT_RULE_END
        if is_moat_period and monthly_pnl > 0:
            status = "鎖定獲利期：禁止提領，100% 再投入"
            logger.info(f"Moat Rule active. Result: {status}")
            return {"eligible": False, "status": status}

        # Happiness Incentive
        kpi_criteria = UPGRADE_CRITERIA[self.current_scale]
        kpi_met = risk_reward_ratio >= kpi_criteria['rr_key'] and win_rate >= kpi_criteria['wr_key']

        if monthly_pnl > 0 and kpi_met:
            incentive_amount = monthly_pnl * 0.10
            result = {
                "eligible": True,
                "amount": int(round(incentive_amount)),
                "distribution": f"Wife: {int(round(incentive_amount * 0.5))}, Self: {int(round(incentive_amount * 0.5))}"
            }
            logger.info(f"Happiness Incentive is eligible. Amount: {result['amount']}.")
            return result
        elif monthly_pnl > 0 and not kpi_met:
            logger.info("Happiness Incentive not eligible: KPI not met, profit reserved.")
            return {"eligible": False, "status": "獲利保留補考"}
        else:
            logger.info("Happiness Incentive not eligible: No profit this month.")
            return {"eligible": False, "status": "No profit this month."}

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

        for month, group in monthly_groups:
            if group.empty:
                continue
            
            month_str = month.strftime('%Y-%m')
            win_rate, rr, pnl = self._calculate_kpis(group)

            # --- Monthly Evaluations ---
            # NOTE: These evaluations use the current audit's capital context for all historical months.
            risk_check = self._check_safety_valves(group)
            evaluation = self._evaluate_capital_management(win_rate, rr)
            incentive = self._evaluate_life_strategy(pnl, win_rate, rr)
            
            summary = {
                "month": month_str,
                "total_pnl": float(round(pnl, 2)),
                "win_rate": f"{win_rate:.2%}",
                "risk_reward_ratio": f"{rr:.2f}",
                "trade_count": len(group),
                "risk_check": risk_check,
                "evaluation": evaluation,
                "incentive": incentive,
            }
            summary_list.append(summary)
            
            # Prepare detailed trades for this month
            # Convert timestamp to string for JSON serialization
            group_copy = group.copy()
            group_copy['trade_time'] = group_copy['trade_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
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
            
            win_rate, risk_reward_ratio, total_pnl = self._calculate_kpis(trades)
            
            safety_checks = self._check_safety_valves(trades)
            safety_checks['night_session_violations'] = self._check_night_session(trades)
            
            evaluation = self._evaluate_capital_management(win_rate, risk_reward_ratio)
            evaluation['happiness_incentive'] = self._evaluate_life_strategy(total_pnl, win_rate, risk_reward_ratio)

            # Calculate the historical monthly summary and the detailed trades
            monthly_summary, monthly_trades = self.calculate_monthly_summary(trades)

            # 5. Construct the final report
            report = {
                "report_date": self.report_date,
                "account_status": {"scale": self.current_scale, "balance": self.current_capital, "monthly_pnl": float(round(total_pnl, 2))},
                "kpi_metrics": {"win_rate": f"{win_rate:.2%}", "risk_reward_ratio": f"{risk_reward_ratio:.2f}"},
                "safety_checks": safety_checks,
                "evaluation": evaluation,
                "monthly_summary": monthly_summary,
                "monthly_trades": monthly_trades, # Add the new detailed trades to the report
                "upgrade_criteria": UPGRADE_CRITERIA,
            }
            logger.info(f"--- Audit Completed Successfully ---")
            return report
        except Exception as e:
            logger.critical(f"A critical error occurred during the audit run: {e}", exc_info=True)
            raise

# --- Example Usage ---
if __name__ == '__main__':
    trade_data_directory = 'tradedata'
    logger.info("Executing TradeAuditor as a standalone script.")
    try:
        latest_file_path = find_latest_trade_file(trade_data_directory)
        
        logger.info("\n--- Running Scenario 1: Upgrade Fails (Capital Key) ---")
        auditor_s1 = TradeAuditor(current_capital=185000, monthly_start_capital=173000, current_scale="S1")
        report_s1 = auditor_s1.run_audit(latest_file_path)
        print(json.dumps(report_s1, indent=2, ensure_ascii=False))
        
        logger.info("\n--- Running Scenario 2: Upgrade Succeeds ---")
        auditor_s2 = TradeAuditor(current_capital=210000, monthly_start_capital=198000, current_scale="S1")
        report_s2 = auditor_s2.run_audit(latest_file_path)
        print(json.dumps(report_s2, indent=2, ensure_ascii=False))

        logger.info("\n--- Running Scenario 3: Monthly Circuit Breaker ---")
        auditor_s3 = TradeAuditor(current_capital=140000, monthly_start_capital=200000, current_scale="S2")
        report_s3 = auditor_s3.run_audit(latest_file_path)
        print(json.dumps(report_s3, indent=2, ensure_ascii=False))

    except FileNotFoundError as e:
        logger.error(f"Error in script execution: {e}", exc_info=True)
        print(f"Error: {e}")
    except Exception as e:
        logger.critical(f"An unexpected critical error occurred in the main script block: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}")
