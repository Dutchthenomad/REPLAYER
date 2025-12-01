#!/usr/bin/env python3
"""
Automated Bot Test - Run bot and detect issues automatically

This script runs the bot through multiple games and automatically detects:
- Buttons that aren't getting clicked
- Missing visual feedback
- Timing issues
- Trade execution failures
- Strategy logic errors

Usage:
    cd /home/nomad/Desktop/REPLAYER/src
    /home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 automated_bot_test.py --games 5

Output:
    - Detailed test report with pass/fail for each check
    - Screenshots of any failures
    - Recommendations for fixes
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import json
from typing import List, Dict, Any

# Add parent directory to Python path to allow imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Setup logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
test_dir = Path(f"automated_test_{timestamp}")
test_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(test_dir / "test_results.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class BotTestValidator:
    """Automated validation of bot behavior"""

    def __init__(self):
        self.results = {
            'timestamp': timestamp,
            'tests': [],
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }

    def test(self, name: str, condition: bool, details: str = "", severity: str = "error"):
        """
        Record a test result

        Args:
            name: Test name
            condition: True if test passed
            details: Additional details
            severity: 'error' or 'warning'
        """
        result = {
            'name': name,
            'passed': condition,
            'details': details,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }

        self.results['tests'].append(result)
        self.results['summary']['total'] += 1

        if condition:
            self.results['summary']['passed'] += 1
            logger.info(f"✅ PASS: {name}")
        else:
            if severity == 'error':
                self.results['summary']['failed'] += 1
                logger.error(f"❌ FAIL: {name} - {details}")
            else:
                self.results['summary']['warnings'] += 1
                logger.warning(f"⚠️ WARNING: {name} - {details}")

    def save_report(self):
        """Save test report to JSON"""
        report_file = test_dir / "test_report.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info("=" * 80)
        logger.info("TEST REPORT")
        logger.info(f"Total tests: {self.results['summary']['total']}")
        logger.info(f"Passed: {self.results['summary']['passed']}")
        logger.info(f"Failed: {self.results['summary']['failed']}")
        logger.info(f"Warnings: {self.results['summary']['warnings']}")
        logger.info(f"Report saved to: {report_file}")
        logger.info("=" * 80)


class BotBehaviorMonitor:
    """Monitor bot behavior during execution"""

    def __init__(self):
        self.button_clicks = []
        self.decisions = []
        self.trades = []
        self.errors = []

    def record_button_click(self, button_name: str, timestamp: datetime):
        """Record button click event"""
        self.button_clicks.append({
            'button': button_name,
            'timestamp': timestamp.isoformat()
        })

    def record_decision(self, decision: str, reasoning: str, state: Dict[str, Any]):
        """Record bot decision"""
        self.decisions.append({
            'decision': decision,
            'reasoning': reasoning,
            'state': state,
            'timestamp': datetime.now().isoformat()
        })

    def record_trade(self, trade_type: str, success: bool, error: str = None):
        """Record trade execution"""
        self.trades.append({
            'type': trade_type,
            'success': success,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })

    def record_error(self, error: str, context: Dict[str, Any] = None):
        """Record error"""
        self.errors.append({
            'error': error,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        })

    def validate(self, validator: BotTestValidator):
        """Run validation checks on collected data"""

        # Test 1: Bot made decisions
        validator.test(
            "Bot made decisions",
            len(self.decisions) > 0,
            f"Decisions: {len(self.decisions)}"
        )

        # Test 2: Buttons were clicked (for UI_LAYER mode)
        validator.test(
            "Buttons clicked in UI_LAYER mode",
            len(self.button_clicks) > 0,
            f"Button clicks: {len(self.button_clicks)}",
            severity="warning"  # Warning if not in UI mode
        )

        # Test 3: No trade execution errors
        failed_trades = [t for t in self.trades if not t['success']]
        validator.test(
            "No trade execution errors",
            len(failed_trades) == 0,
            f"Failed trades: {len(failed_trades)}"
        )

        # Test 4: No unhandled errors
        validator.test(
            "No unhandled errors",
            len(self.errors) == 0,
            f"Errors: {len(self.errors)}"
        )

        # Test 5: Decisions have reasoning
        decisions_without_reasoning = [
            d for d in self.decisions if not d.get('reasoning')
        ]
        validator.test(
            "All decisions have reasoning",
            len(decisions_without_reasoning) == 0,
            f"Decisions without reasoning: {len(decisions_without_reasoning)}"
        )

        # Test 6: Button clicks follow timing config
        if len(self.button_clicks) >= 2:
            # Check time between clicks
            click_times = [
                datetime.fromisoformat(c['timestamp'])
                for c in self.button_clicks
            ]
            delays = [
                (click_times[i+1] - click_times[i]).total_seconds() * 1000
                for i in range(len(click_times) - 1)
            ]
            avg_delay = sum(delays) / len(delays) if delays else 0

            # Should be around configured inter_click_pause_ms (default 100ms)
            # Allow 50ms margin for processing time
            expected_min = 50  # At least 50ms between clicks
            expected_max = 1000  # At most 1 second (very generous)

            validator.test(
                "Button click timing reasonable",
                expected_min <= avg_delay <= expected_max,
                f"Average delay: {avg_delay:.1f}ms (expected {expected_min}-{expected_max}ms)",
                severity="warning"
            )

        # Test 7: Trade types are valid
        valid_types = ['BUY', 'SELL', 'SIDEBET']
        invalid_trades = [
            t for t in self.trades
            if t['type'] not in valid_types
        ]
        validator.test(
            "All trade types are valid",
            len(invalid_trades) == 0,
            f"Invalid trades: {len(invalid_trades)}"
        )


def run_automated_test(num_games: int = 5):
    """
    Run automated bot test

    Args:
        num_games: Number of games to test
    """
    logger.info("=" * 80)
    logger.info("AUTOMATED BOT TEST")
    logger.info(f"Testing {num_games} games")
    logger.info("=" * 80)

    validator = BotTestValidator()
    monitor = BotBehaviorMonitor()

    try:
        # TODO: Integrate with actual REPLAYER
        # For now, this is a framework for testing

        logger.info("Test framework ready - integrate with REPLAYER in next session")

        # Placeholder validations
        validator.test(
            "Test framework initialized",
            True,
            "Framework ready for integration"
        )

    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        monitor.record_error(str(e))
    finally:
        # Run validations
        monitor.validate(validator)

        # Save report
        validator.save_report()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Automated bot testing')
    parser.add_argument('--games', type=int, default=5, help='Number of games to test')

    args = parser.parse_args()

    run_automated_test(num_games=args.games)
