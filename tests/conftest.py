# Copyright 2026 Telefónica Soluciones de Informática y Comunicaciones de España, S.A.U.
#
# This file includes or is based on software originally developed by Confluent Inc.
# and has been modified by Telefónica Soluciones de Informática y Comunicaciones
# de España, S.A.U.
#
# Licensed under the Confluent Community License, Version 1.0.
# You may obtain a copy of the License at:
#
#   http://www.confluent.io/confluent-community-license
#
# This software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied.

from dotenv import load_dotenv
load_dotenv(override=True)

from common_test import multiservice_stack

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """
    Print a summary of the test results at the end of the test run.
    """
    terminalreporter.write_sep("=", "📋 Scenario Summary")
    for report in terminalreporter.stats.get("passed", []):
        if report.when == "call":
            terminalreporter.write_line(f"✅ {report.nodeid}")
    for report in terminalreporter.stats.get("failed", []):
        if report.when == "call":
            terminalreporter.write_line(f"❌ {report.nodeid}")