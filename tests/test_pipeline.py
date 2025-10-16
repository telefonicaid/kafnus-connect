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

import pytest
from utils.scenario_loader import load_scenario
from utils.kafka_producer import load_input, produce_messages
from utils.postgis_validator import PostgisValidator
from utils.mongo_validator import MongoValidator
from utils.http_validator import HttpValidator
from utils.sql_runner import execute_sql_file
from config import logger
from utils.scenario_loader import discover_scenarios, load_description
from config import DEFAULT_DB_CONFIG
import time

@pytest.mark.parametrize("scenario_name, expected_list, input_json, setup", discover_scenarios())
def test_e2e_pipeline(scenario_name, expected_list, input_json, setup, multiservice_stack):
    logger.info(f"🧪 Running scenario: {scenario_name}")
    kafka_cfg = multiservice_stack["kafka"]

    # Step 0: Description
    scenario_dir = input_json.parent
    desc = load_description(scenario_dir)
    if desc:
        logger.info(f"0. Description: {desc}")
    # Step 0.5: Setup DB if needed
    if setup:
        execute_sql_file(setup, db_config=DEFAULT_DB_CONFIG)

    # Step 1: produce messages to Kafka
    input_data = load_input(input_json)
    produce_messages(kafka_cfg, input_data)

    # Step 2: wait a few seconds for sinks to process
    time.sleep(5)

    # Step 3: validate expected outputs (Postgres / HTTP / etc)
    all_valid = True
    errors = []

    for expected_type, expected_json in expected_list:
        expected_data = load_scenario(expected_json, as_expected=True)

        if expected_type == "pg":
            validator = PostgisValidator(DEFAULT_DB_CONFIG)
            for table_data in expected_data:
                table = table_data["table"]
                if not validator.validate(table, table_data["rows"]):
                    all_valid = False
                    errors.append(f"❌ PG validation failed for {table}")

        elif expected_type == "mongo":
                validator = MongoValidator()
                try:
                    for coll_data in expected_data:
                        coll = coll_data["collection"]
                        if "documents" in coll_data:
                            if not validator.validate(coll, coll_data["documents"]):
                                all_valid = False
                                errors.append(f"❌ Mongo validation failed in {coll}")
                        if "absent" in coll_data:
                            if not validator.validate_absent(coll, coll_data["absent"]):
                                all_valid = False
                                errors.append(f"❌ Mongo forbidden docs in {coll}")
                finally:
                    validator.close()

        elif expected_type == "http":
            validator = HttpValidator()
            for req in expected_data:
                if not validator.validate(req):
                    all_valid = False
                    errors.append(f"❌ HTTP validation failed: {req['url']}")

    assert all_valid, "\n".join(errors)
