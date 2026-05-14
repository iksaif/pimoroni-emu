"""Tufty 2350 launcher entry point.

The Pimoroni launcher imports this when its tile is selected; we
bootstrap the working directory + sys.path and hand off to main().
"""

import os
import sys

APP_DIR = "/system/apps/wifi_health"
sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)

from main import main

main()
