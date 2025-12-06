
import os
import subprocess
import json
import pytest

# --- Test Setup and Teardown ---

@pytest.fixture(scope="module")
def project_root():
    """Return the root directory of the project."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(scope="module")
def test_data_dir(project_root):
    """Create a temporary directory for test data."""
    data_dir = os.path.join(project_root, 'tests', 'test_data')
    os.makedirs(data_dir, exist_ok=True)
    yield data_dir
    # Cleanup
    for f in os.listdir(data_dir):
        os.remove(os.path.join(data_dir, f))
    os.rmdir(data_dir)

@pytest.fixture(scope="module")
def config_file(test_data_dir):
    """Create a dummy config.ini file for testing."""
    config_content = """
[Account]
current_capital = 100000
monthly_start_capital = 100000
current_scale = S1
operation_contracts = 1
"""
    config_path = os.path.join(test_data_dir, 'config.ini')
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    return config_path

@pytest.fixture(scope="module")
def trade_data_file(test_data_dir):
    """Create a dummy trade data CSV file."""
    csv_content = """
成交時間,買賣別,平倉損益淨額,口數,商品名稱
2025/12/01 09:00:00,Buy,1000,1,小型臺指
2025/12/01 09:15:00,Sell,-500,1,小型臺指
2025/12/01 09:30:00,Buy,2000,2,微型臺指
"""
    csv_path = os.path.join(test_data_dir, 'dummy_trades.csv')
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write(csv_content)
    return csv_path

# --- Test Cases ---

def test_trade_check_script_runs_successfully(project_root, config_file, trade_data_file):
    """
    Test that the trade_check.py script runs without errors and generates a valid JSON report.
    This test specifically ensures that the numpy int64 serialization bug is fixed.
    """
    # --- Arrange ---
    script_path = os.path.join(project_root, 'trade_check.py')
    output_json_path = os.path.join(project_root, 'audit_report.json')
    
    # Temporarily move config to project root for the script to find it
    temp_config_path = os.path.join(project_root, 'config.ini')
    os.rename(config_file, temp_config_path)

    # --- Act ---
    # Run the script as a subprocess
    result = subprocess.run(
        ['python', script_path, '--file', trade_data_file],
        capture_output=True,
        text=True,
        cwd=project_root
    )

    # --- Assert ---
    # Check that the script ran successfully
    assert result.returncode == 0, f"Script failed with exit code {result.returncode}. Stderr: {result.stderr}"
    
    # Check that the report was generated
    assert os.path.exists(output_json_path), "audit_report.json was not created."
    
    # Check that the report is valid JSON
    try:
        with open(output_json_path, 'r', encoding='utf-8') as f:
            json.load(f)
    except json.JSONDecodeError:
        pytest.fail("Generated report is not valid JSON.")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred while reading the report: {e}")

    # --- Cleanup ---
    os.remove(output_json_path)
    os.remove(temp_config_path)
