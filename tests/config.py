# Copyright 2025 Telefónica Soluciones de Informática y Comunicaciones de España, S.A.U.
# PROJECT: Kafnus
#
# This software and / or computer program has been developed by Telefónica Soluciones
# de Informática y Comunicaciones de España, S.A.U (hereinafter TSOL) and is protected
# as copyright by the applicable legislation on intellectual property.
#
# It belongs to TSOL, and / or its licensors, the exclusive rights of reproduction,
# distribution, public communication and transformation, and any economic right on it,
# all without prejudice of the moral rights of the authors mentioned above. It is expressly
# forbidden to decompile, disassemble, reverse engineer, sublicense or otherwise transmit
# by any means, translate or create derivative works of the software and / or computer
# programs, and perform with respect to all or part of such programs, any type of exploitation.
#
# Any use of all or part of the software and / or computer program will require the
# express written consent of TSOL. In all cases, it will be necessary to make
# an express reference to TSOL ownership in the software and / or computer
# program.
#
# Non-fulfillment of the provisions set forth herein and, in general, any violation of
# the peaceful possession and ownership of these rights will be prosecuted by the means
# provided in both Spanish and international law. TSOL reserves any civil or
# criminal actions it may exercise to protect its rights.
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Directory where all scenario test cases are stored
SCENARIOS_DIR = Path(__file__).parent / "cases"

# Default database configuration used for testing, with env vars supports
DEFAULT_DB_CONFIG = {
    "host": os.getenv("KAFNUS_TESTS_PG_HOST", "localhost"),
    "port": int(os.getenv("KAFNUS_TESTS_PG_PORT", 5432)),
    "dbname": os.getenv("KAFNUS_TESTS_PG_DBNAME", "tests"),
    "user": os.getenv("KAFNUS_TESTS_PG_USER", "postgres"),
    "password": os.getenv("KAFNUS_TESTS_PG_PASSWORD", "postgres"),
}

# Kafnus Connect default endpoint
KAFNUS_TESTS_KAFNUS_CONNECT_URL = os.getenv("KAFNUS_TESTS_KAFNUS_CONNECT_URL", "http://localhost:8083")

# Default connector name for health-check
KAFNUS_TESTS_DEFAULT_CONNECTOR_NAME = os.getenv("KAFNUS_TESTS_DEFAULT_CONNECTOR_NAME", "http-sink")

# Setup and start logger
def setup_test_logger(name="kafnus-tests"):
    """
    Initializes and returns a structured logger for test execution.
    Supports standard log levels: DEBUG, INFO, WARN, ERROR, FATAL.
    Also silences noisy external libraries (Kafka, urllib3, etc.)
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "FATAL": logging.CRITICAL,
        "CRITICAL": logging.CRITICAL
    }

    raw_level = os.getenv("KAFNUS_TESTS_LOG_LEVEL", "INFO").upper()
    log_level = level_map.get(raw_level, logging.INFO)

    # --- Configure main app logger ---
    logging.basicConfig(
        level=log_level,
        format="time=%(asctime)s | lvl=%(levelname)s | comp=KAFNUS-TESTS | op=%(name)s:%(filename)s[%(lineno)d]:%(funcName)s | msg=%(message)s",
        handlers=[logging.StreamHandler()]
    )

    logger = logging.getLogger(name)

    # --- Silence noisy external libraries ---
    noisy_libs = [
        "kafka",          # kafka-python internals
        "urllib3",        # requests, etc.
        "asyncio",        # testcontainers async loop
        "faker.factory",  # sometimes used in tests
        "aiohttp.access"
    ]
    for lib in noisy_libs:
        logging.getLogger(lib).setLevel(logging.WARNING)
        logging.getLogger(lib).propagate = False

    return logger


logger = setup_test_logger()
