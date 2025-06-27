#!/usr/bin/env python3
"""
Test script to verify logging functionality.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to import run_automation
sys.path.append(str(Path(__file__).parent))

# Import the logger from run_automation
from automation.run_automation import logger, LOGS_DIR

def test_logging():
    """Test logging functionality."""
    print(f"Testing logging to directory: {LOGS_DIR}")
    
    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Verify log file was created
    log_file = Path(LOGS_DIR) / 'scraper_automation.log'
    print(f"Log file should be at: {log_file}")
    
    if log_file.exists():
        print("\nLog file contents:")
        print("-" * 50)
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                print(f.read())
        except Exception as e:
            print(f"Error reading log file: {e}")
    else:
        print("\nError: Log file was not created!")
        
    return log_file.exists()

if __name__ == "__main__":
    print("Starting logging test...")
    success = test_logging()
    if success:
        print("\n✅ Logging test completed successfully!")
    else:
        print("\n❌ Logging test failed!")
    sys.exit(0 if success else 1)
