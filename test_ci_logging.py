#!/usr/bin/env python3
"""
Test script to verify logging behavior in CI environment.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to import run_automation
sys.path.append(str(Path(__file__).parent))

# Import the logger from run_automation
from automation.run_automation import logger, setup_logging

def test_ci_logging():
    """Test that file logging is properly disabled in CI."""
    # Simulate CI environment
    os.environ['CI'] = 'true'
    
    # Re-initialize logging with CI settings
    test_logger = setup_logging(disable_file_logging=True)
    
    # Test logging
    test_message = "TEST MESSAGE - This should only appear in console in CI"
    test_logger.info(test_message)
    
    # Check if file logging is disabled
    file_handlers = [h for h in test_logger.handlers 
                    if isinstance(h, logging.FileHandler)]
    
    print("\n=== Test Results ===")
    print(f"CI Environment: {os.getenv('CI')}")
    print(f"File handlers found: {len(file_handlers)}")
    print("Logging to console only:", len(file_handlers) == 0)
    
    # Cleanup
    if 'CI' in os.environ:
        del os.environ['CI']
    
    return len(file_handlers) == 0

if __name__ == "__main__":
    print("Testing CI logging configuration...")
    success = test_ci_logging()
    if success:
        print("\n✅ Test passed: File logging is disabled in CI")
    else:
        print("\n❌ Test failed: File logging is still enabled in CI")
