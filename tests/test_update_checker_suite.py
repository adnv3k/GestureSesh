#!/usr/bin/env python3
"""
Test runner for update checker functionality.
Runs both unit tests and debug analysis for comprehensive testing.
"""

import sys
import os
import unittest
import argparse
from pathlib import Path

# Add the src directory and tests directory to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))
sys.path.insert(0, project_root)

try:
    from tests.test_update_checker import test_changelog_parsing
    from tests.debug_changelog import debug_changelog
except ImportError as e:
    print(f"Error: Could not import test modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)


def run_unit_tests(verbose=True):
    """Run the unit tests for update checker."""
    print("=" * 60)
    print("RUNNING UPDATE CHECKER TESTS")
    print("=" * 60)
    
    try:
        test_changelog_parsing()
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def run_debug_analysis(current_version="0.4.0"):
    """Run debug analysis for changelog parsing."""
    print("\n" + "=" * 60)
    print("RUNNING DEBUG ANALYSIS")
    print("=" * 60)
    
    try:
        debug_changelog()
        return True
    except Exception as e:
        print(f"❌ Debug analysis failed: {e}")
        return False


def run_integration_test():
    """Run integration test that combines both approaches."""
    print("\n" + "=" * 60)
    print("RUNNING INTEGRATION TEST")
    print("=" * 60)
    
    try:
        # Run the simple test again as integration test
        test_changelog_parsing()
        return True
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Test update checker functionality")
    parser.add_argument(
        "--mode",
        choices=["unit", "debug", "integration", "all"],
        default="all",
        help="Test mode to run (default: all)"
    )
    parser.add_argument(
        "--version",
        default="0.4.0",
        help="Current version to simulate (default: 0.4.0)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    parser.add_argument(
        "--no-network",
        action="store_true",
        help="Skip tests that require network access"
    )
    
    args = parser.parse_args()
    
    print("GestureSesh Update Checker Test Suite")
    print(f"Simulating current version: {args.version}")
    if args.no_network:
        print("⚠️ Network tests will be skipped")
    print()
    
    results = []
    
    if args.mode in ["unit", "all"]:
        print("Running unit tests...")
        success = run_unit_tests(verbose=not args.quiet)
        results.append(("Unit Tests", success))
    
    if args.mode in ["debug", "all"] and not args.no_network:
        print("Running debug analysis...")
        success = run_debug_analysis(args.version)
        results.append(("Debug Analysis", success))
    elif args.mode in ["debug", "all"] and args.no_network:
        print("Skipping debug analysis (--no-network specified)")
    
    if args.mode in ["integration", "all"] and not args.no_network:
        print("Running integration test...")
        success = run_integration_test()
        results.append(("Integration Test", success))
    elif args.mode in ["integration", "all"] and args.no_network:
        print("Skipping integration test (--no-network specified)")
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:<20}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\nOverall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
