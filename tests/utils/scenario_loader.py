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
import os
from pathlib import Path
from typing import Optional, List, Tuple
from config import SCENARIOS_DIR, logger

def discover_scenarios() -> List[Tuple[str, List[Tuple[str, Path]], Path, Optional[Path]]]:
    """
    Recursively discovers all test scenarios under SCENARIOS_DIR.

    Returns a list of tuples:
    - scenario name (relative path from SCENARIOS_DIR)
    - list of (expected_type, expected_path) for expected_*.json
    - path to input.json (messages to produce to Kafka)
    - optional path to setup.sql
    """
    logger.debug(f"🔍 Scanning for test scenarios in: {SCENARIOS_DIR}")
    scenarios = []

    for dirpath, _, filenames in os.walk(SCENARIOS_DIR):
        dir_path = Path(dirpath)
        input_json = dir_path / "input.json"
        setup_sql = dir_path / "setup.sql"

        if not input_json.exists():
            continue  # skip directories without input.json

        # Gather expected_* JSON files
        expected_files = []
        for f in filenames:
            if f.startswith("expected_") and f.endswith(".json"):
                expected_type = f[len("expected_") : -len(".json")]
                expected_files.append((expected_type, dir_path / f))

        relative_name = str(dir_path.relative_to(SCENARIOS_DIR))
        logger.debug(f"✅ Found scenario: {relative_name} with expected types {[e[0] for e in expected_files]}")

        scenarios.append(
            (
                relative_name,
                expected_files,
                input_json,
                setup_sql if setup_sql.exists() else None
            )
        )

    scenarios.sort(key=lambda c: c[0])
    logger.debug(f"🔢 Total scenarios discovered: {len(scenarios)}")
    return scenarios


def load_scenario(json_path: Path, as_expected: bool = False):
    """
    Loads a test scenario JSON file.

    Parameters:
    - json_path: Path to the JSON scenario file.
    - as_expected: True if loading expected output (Postgres/Mongo/HTTP), False for Kafka input messages.

    Returns:
    - List of dictionaries (messages or expected results)
    """
    logger.debug(f"📂 Loading scenario file: {json_path}")
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, list) else [data]


def load_description(scenario_dir: Path) -> Optional[str]:
    """
    Loads a human-readable description from description.txt if present.

    Parameters:
    - scenario_dir: Path to the scenario directory

    Returns:
    - Description string or None
    """
    desc_path = scenario_dir / "description.txt"
    if desc_path.exists():
        return desc_path.read_text(encoding="utf-8").strip()
    return None
