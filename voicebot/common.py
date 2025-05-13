# Copyright (C) 2025 Cisco Systems, Inc.

import logging

# Centralized logging configuration
logger = logging.getLogger("rtc_app")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
