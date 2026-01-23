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

from config import logger
import psycopg2

def execute_sql_file(sql_path, db_config):
    """
    Executes the SQL statements in the given file against a PostgreSQL database.

    Connects to the database using the provided configuration, reads the SQL file,
    and executes its content within a transaction. Closes the connection after execution.

    Parameters:
    - sql_path: Path to the .sql file to execute.
    - db_config: Dictionary with keys: dbname, user, password, host, and port.

    Raises:
    - Exception if SQL execution or database connection fails.
    """
    logger.debug(f"📄 Executing SQL from: {sql_path}")
    logger.debug(f"🔗 Connecting to DB: {db_config['host']}:{db_config['port']}, DB: {db_config['dbname']}")

    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    try:
        conn = psycopg2.connect(**db_config)
        logger.debug("✅ Connection established")

        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                logger.info("✅ SQL executed successfully")
    except Exception as e:
        logger.error(f"❌ Error executing SQL from {sql_path}: {e}")
        raise
    finally:
        conn.close()
        logger.debug("🔌 Connection closed")
