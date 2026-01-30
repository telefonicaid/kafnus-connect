# Copyright 2026 Telefónica Soluciones de Informática y Comunicaciones de España, S.A.U.
#
# This file is part of kafnus-connect
#
# kafnus-connect is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# kafnus-connect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with kafnus. If not, see http://www.gnu.org/licenses/.

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