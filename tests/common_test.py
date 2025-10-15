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

import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Union
import pytest
import requests
#from testcontainers.compose import DockerCompose
from testcontainers.compose import DockerCompose as OriginalDockerCompose
import subprocess
import os
from utils.kafnus_connect_loader import deploy_all_sinks
import time

from config import logger
from typing import Optional
from utils.wait_services import wait_for_kafnus_connect, wait_for_connector, wait_for_postgres, wait_for_orion, ensure_postgis_db_ready, wait_for_kafnus_ngsi

# ──────────────────────────────
# Utils
# ──────────────────────────────

def read_files(file_path: Path):
    """
    Loads and returns the contents of a JSON file from the specified path.
    Raises an exception if the file does not exist or cannot be read.

    Parameters:
    - file_path: Path to the JSON file.

    Returns:
    - Parsed JSON content.
    """
    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise Exception(f"the file {file_path} does not exist") from exc

# ──────────────────────────────
# Data classes
# ──────────────────────────────

@dataclass
class MultiServiceContainer:
    orionHost: str
    orionPort: str
    kafkaHost: str
    kafkaPort: str
    kafkaConnectHost: str
    KafkaConnectPort: str

@dataclass
class KafkaMessages:
    topic: str
    headers: dict
    message: dict


# ──────────────────────────────
# Testcontainers Fixture
# ──────────────────────────────
class DockerCompose(OriginalDockerCompose):
    """
    This subclass overrides the original Testcontainers DockerCompose class
    to use the newer Docker Compose V2 CLI ("docker compose") instead of
    the default Docker Compose V1 CLI ("docker-compose") which Testcontainers
    uses by default. This ensures compatibility with the latest Docker CLI,
    improving command support and avoiding deprecated syntax.
    """
    def __init__(self, filepath: str, compose_file_name: Union[str, List[str]] = "docker-compose.yml", **kwargs):
        if isinstance(compose_file_name, str):
            compose_file_name = [compose_file_name]
        self.compose_file_name = compose_file_name
        super().__init__(filepath, compose_file_name=compose_file_name, **kwargs)
    
    def _call_command(self, cmd: List[str]) -> None:
        """Override to use docker compose instead of docker-compose"""
        if cmd and cmd[0] == "docker-compose":
            cmd = ["docker", "compose"] + cmd[1:]
        super()._call_command(cmd)
    
    def _build_compose_command(self, subcommand: str) -> List[str]:
        """Build a docker compose command with all compose files"""
        cmd = ["docker", "compose"]
        for compose_file in self.compose_file_name:
            cmd.extend(["-f", str(Path(self.filepath) / compose_file)])
        cmd.append(subcommand)
        return cmd
    
    def _wait_for_service(self, service_name: str, port: int, timeout: int = 30):
        """Wait until the service is responding to port queries"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                cmd = self._build_compose_command("port")
                cmd.extend([service_name, str(port)])
                subprocess.check_output(cmd, cwd=self.filepath, stderr=subprocess.PIPE)
                return True
            except subprocess.CalledProcessError:
                time.sleep(1)
        return False
    
    def get_service_host(self, service_name: str, port: int) -> str:
        if not self._wait_for_service(service_name, port):
            raise RuntimeError(f"Service {service_name} port {port} not available after waiting")
        
        port_cmd = self._build_compose_command("port")
        port_cmd.extend([service_name, str(port)])
        
        try:
            output = subprocess.check_output(port_cmd, cwd=self.filepath).decode("utf-8")
            return output.split(":")[0].strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get service host for {service_name}:{port}. Is the service running and the port exposed?") from e
    
    def get_service_port(self, service_name: str, port: int) -> int:
        if not self._wait_for_service(service_name, port):
            raise RuntimeError(f"Service {service_name} port {port} not available after waiting")
        
        port_cmd = self._build_compose_command("port")
        port_cmd.extend([service_name, str(port)])
        
        try:
            output = subprocess.check_output(port_cmd, cwd=self.filepath).decode("utf-8")
            return int(output.split(":")[1].strip())
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get service port for {service_name}:{port}") from e
        except (IndexError, ValueError) as e:
            raise RuntimeError(f"Unexpected output format from docker compose port command") from e
    

@pytest.fixture(scope="session")
def multiservice_stack():
    """
    Deploys Kafka, Kafnus Connect, and target sinks
    (e.g., PostgreSQL, MongoDB and HTTP mock) using Testcontainers.
    """
    docker_dir = Path(__file__).resolve().parent / "docker"
    compose_files = [
        "docker-compose.yml"
    ]

    with DockerCompose(str(docker_dir), compose_file_name=compose_files) as compose:
        kafka_host = compose.get_service_host("kafka", 9092)
        kafka_port = compose.get_service_port("kafka", 9092)
        connect_host = compose.get_service_host("kafnus-connect", 8083)
        connect_port = compose.get_service_port("kafnus-connect", 8083)

        # Setup PostgreSQL DB with PostGIS extension
        KAFNUS_TESTS_PG_HOST = os.getenv("KAFNUS_TESTS_PG_HOST", "localhost")
        KAFNUS_TESTS_PG_PORT = int(os.getenv("KAFNUS_TESTS_PG_PORT", "5432"))
        KAFNUS_TESTS_PG_USER = os.getenv("KAFNUS_TESTS_PG_USER", "postgres")
        KAFNUS_TESTS_PG_PASSWORD = os.getenv("KAFNUS_TESTS_PG_PASSWORD", "postgres")

        # Wait for services to be ready and deploy sinks
        sinks_dir = Path(__file__).resolve().parent / "sinks"
        wait_for_postgres(KAFNUS_TESTS_PG_HOST, KAFNUS_TESTS_PG_PORT)
        ensure_postgis_db_ready(KAFNUS_TESTS_PG_HOST, KAFNUS_TESTS_PG_PORT, KAFNUS_TESTS_PG_USER, KAFNUS_TESTS_PG_PASSWORD)
        wait_for_kafnus_connect()
        logger.info("🚀 Deployings sinks...")
        deploy_all_sinks(sinks_dir)
        wait_for_connector()
        wait_for_connector("jdbc-historical-sink")
        wait_for_connector("mongo-sink")

        yield {
            "kafka": f"{kafka_host}:{kafka_port}",
            "kafnus-connect": f"http://{connect_host}:{connect_port}",
            "postgres": {"host": KAFNUS_TESTS_PG_HOST, "port": KAFNUS_TESTS_PG_PORT}
        }
    
        # If the KAFNUS_TESTS_E2E_MANUAL_INSPECTION env var is set to "true", the test will pause
        # before stopping containers, to allow manual inspection.
        if os.getenv("KAFNUS_TESTS_E2E_MANUAL_INSPECTION", "false").lower() == "true":
            logger.info("🧪 Pausing for manual inspection. Ctrl+C to terminate.")
            time.sleep(3600)
    
    logger.info("✅ Tests have finished")
