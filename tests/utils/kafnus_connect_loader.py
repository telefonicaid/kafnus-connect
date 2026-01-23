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
#
# Authors:
#  - Álvaro Vega
#  - Gregorio Blázquez
#  - Fermín Galán
#  - Oriana Romero

import json
import requests
from pathlib import Path

from config import logger
from config import KAFNUS_TESTS_KAFNUS_CONNECT_URL

def deploy_all_sinks(sinks_dir: Path, kafnus_connect_url: str = KAFNUS_TESTS_KAFNUS_CONNECT_URL):
    """
    Deploys all Kafnus Connect sink connectors defined as JSON files in the given directory.

    For each JSON file:
    - Loads the configuration.
    - Extracts the connector name.
    - Sends a POST request to Kafnus Connect to deploy the connector.

    Parameters:
    - sinks_dir: Path to the directory containing JSON sink connector definitions.
    - kafnus_connect_url: URL to the Kafnus Connect REST API (defaults to KAFNUS_TESTS_KAFNUS_CONNECT_URL).
    """
    logger.info(f"📤 Deploying all sinks from directory: {sinks_dir}")

    for file in sinks_dir.glob("*.json"):
        logger.debug(f"🔍 Reading file: {file}")
        with file.open("r", encoding="utf-8") as f:
            config = json.load(f)
        name = config.get("name")

        if not name:
            logger.warning(f"⚠️ File {file.name} does not have 'name', skipping.")
            continue

        try:
            res = requests.post(
                f"{kafnus_connect_url}/connectors",
                headers={"Content-Type": "application/json"},
                json=config
            )
            if res.status_code in [200, 201, 409]:
                logger.info(f"✅ Sink {name} deployed (status: {res.status_code})")
            else:
                logger.error(f"❌ Error deploying {name} : {res.status_code}, {res.text}")
        except Exception as e:
            logger.error(f"❌ Connection error with Kafnus Connect for {name}: {e}")