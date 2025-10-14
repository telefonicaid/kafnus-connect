# ⚙️ Kafnus Connect – Technical Configuration & Plugins

> This document extends the main [README](../README.md) with detailed setup, plugin, and sink configuration information for Kafnus Connect.

---

## 🔄 Overview

This document explains how **Kafnus Connect** is configured to persist NGSI notifications processed by Kafnus NGSI to different data sinks (PostGIS, MongoDB, HTTP).

---

## ⚙️ Environment Setup

This project uses Docker Compose to orchestrate the multi-service environment, including Kafnus Connect and other components.

### 🔊 Adjusting Connector Plugin Log Level

You can control the log level of Kafka Connect plugins using the `CONNECT_LOG4J_LOGGERS` environment variable in your Docker Compose configuration. This is useful for debugging or reducing noise from specific libraries.

```yaml
environment:
CONNECT_LOG4J_LOGGERS: "com.hivemq=DEBUG,org.reflections=ERROR"
```

This sets the log level for the `com.hivemq` connector to `DEBUG` and for `org.reflections` to `ERROR`. You can adjust the value to target other packages or log levels as needed.

**Default configuration:**

```yaml
environment:
CONNECT_LOG4J_LOGGERS: "org.reflections=ERROR"
```

Refer to the [Kafka Connect documentation](https://docs.confluent.io/platform/current/connect/logging.html) for more details on configuring logging.

**Important:**
The `docker-entrypoint.sh` uses environment variables to generate the Kafka Connect configuration and starts Kafka Connect in distributed mode. It also enables the `EnvVarConfigProvider` so connectors can resolve configuration values from environment variables.

### ⚡ docker-entrypoint.sh

The `docker-entrypoint.sh` script generates the Kafka Connect configuration at `/home/appuser/config/connect-distributed.properties` using environment variables, then starts Kafka Connect in distributed mode.

Key environment variables:

* `CONNECT_BOOTSTRAP_SERVERS` (default: `kafka:29092`)
* `CONNECT_GROUP_ID` (default: `connect-cluster`)
* `CONNECT_KEY_CONVERTER` / `CONNECT_VALUE_CONVERTER`
* `CONNECT_PLUGIN_PATH` (default: `/usr/local/share/kafnus-connect/plugins`)
* `CONNECT_REST_PORT` (default: `8083`)

The script ensures defaults are set and logs the final configuration before launching:

```sh
exec "${KAFKA_HOME}/bin/connect-distributed.sh" "${CONFIG_FILE}"
```

> Additionally, the entrypoint enables the `EnvVarConfigProvider`, allowing connectors to resolve configuration values directly from environment variables.

### 💡 Using Environment Variables in Sink Connectors

Kafka Connect uses the [`EnvVarConfigProvider`](https://kafka.apache.org/documentation/#configproviders) to dynamically resolve connector configuration values from environment variables. This allows sink connector definitions (e.g., JDBC or MongoDB) to reference environment variables at runtime using the syntax:

```json
"${env:VARIABLE_NAME}"
```

Example usage inside a connector definition:

```json
"connection.url": "jdbc:postgresql://${env:KAFNUS_TESTS_PG_HOST}:${env:KAFNUS_TESTS_PG_PORT}/${env:KAFNUS_TESTS_PG_DBNAME}"
```

or, for MongoDB:

```json
"connection.uri": "mongodb://${env:KAFNUS_TESTS_MONGO_HOST}:${env:KAFNUS_TESTS_MONGO_PORT}"
```

These variables are defined in the `environment` section of the `kafnus-connect` service in `docker-compose.kafka.yml`:

```yaml

# Environment variables for sinks in tests

KAFNUS_TESTS_PG_HOST: iot-postgis
KAFNUS_TESTS_PG_PORT: "5432"
KAFNUS_TESTS_PG_DBNAME: tests
KAFNUS_TESTS_PG_USER: postgres
KAFNUS_TESTS_PG_PASSWORD: postgres
KAFNUS_TESTS_MONGO_HOST: mongo
KAFNUS_TESTS_MONGO_PORT: "27017"
```

> ✅ These environment variables are available to all sink connectors via `${env:...}` references thanks to the `config.providers=env` setting in the Kafnus Connect distributed configuration.

---

## 🧩 Kafnus Connect Plugins

Kafnus Connect plugins are automatically built into the Docker image and placed under the path defined by the environment variable `CONNECT_PLUGIN_PATH`. By default, this is:

```
/usr/local/share/kafnus-connect/plugins
```

This directory is **populated automatically** during the Docker build using the logic defined in the [Dockerfile](Dockerfile).

### 1. JDBC Plugin for PostGIS

Includes:

* `kafka-connect-jdbc-10.8.4.jar`
* `postgresql-42.7.1.jar`

Used in:

* `pg-sink-historic.json`
* `pg-sink-lastdata.json`
* `pg-sink-mutable.json`
* `pg-sink-errors.json`

### 2. MongoDB Sink Plugin

Includes:

* `mongo-kafka-connect-2.0.1-all.jar` with included MongoDB drivers as (`bson`, `driver-core`, `driver-sync`)

Used in:

* `mdb-sink.json`

> ⚠️ **Warning:** When using `topics.regex` with the MongoDB sink connector, new topics are not automatically picked up unless the connector is redeployed or updated. See the [official MongoDB Kafka docs](https://www.mongodb.com/docs/kafka-connector/current/sink-connector/configuration-properties/kafka-topic/#std-label-sink-configuration-topic-properties).

### 3. HTTP Sink Connector

* **Connector class**: `io.aiven.kafka.connect.http.HttpSinkConnector`
* **Type**: sink
* **Version**: 0.9.0
* **Example config file**: `http-sink.json`
* **Kafka topic**: `tests_http` (configurable)
* **HTTP endpoint**: e.g., `http://localhost:3333`

> Example local test endpoint; replace according to environment.

### 4. Custom SMT – HeaderRouter

Path: `plugins/header-router`

A Java-based Single Message Transform (SMT) implemented in `HeaderRouter.java`. It rewrites the topic name based on a Kafka record header (e.g. `target_table`) set by Kafnus NGSI.

#### SMT Configuration Example

```json
"transforms": "HeaderRouter",
"transforms.HeaderRouter.type": "com.telefonica.HeaderRouter",
"transforms.HeaderRouter.header.key": "target_table"
```

### Other Detected Plugins

These components are either **dependencies needed by the sink plugins** or **source connectors included with the plugin distribution**. They are **not used directly in the Kafnus architecture**:

* `com.mongodb.kafka.connect.MongoSourceConnector` (2.0.1)
* `io.confluent.connect.jdbc.JdbcSourceConnector` (10.8.4)
* MirrorMaker 2 connectors (`MirrorCheckpointConnector`, `MirrorHeartbeatConnector`, `MirrorSourceConnector` – 8.0.0-ccs)

---

## 🗂️ Sink Configurations

The sink connectors are defined under the `sinks/` directory and are responsible for persisting data processed by Kafka (and Kafnus NGSI) to destination databases.

### Configuration files

* `pg-sink-historic.json`: Insert-only, stores immutable historical data.
* `pg-sink-lastdata.json`: Upsert, stores only the latest observation.
* `pg-sink-mutable.json`: Mutable upsert, for data that may change.
* `pg-sink-errors.json`: DLQ for failed records.
* `mdb-sink.json`: MongoDB sink, supports custom database/collection mapping.
* `http-sink.json`: HTTP sink for forwarding to REST endpoints.

> ✅ Historic, lastdata and mutable connectors use the JDBC plugin and the custom `HeaderRouter` SMT.

---

## ▶️ Registering Connectors (it will be updated)

From the `sinks/` directory, register each connector using `curl`:

```bash
curl -X POST http://localhost:8083/connectors 
-H "Content-Type: application/json" 
--data @pg-sink-historic.json
```

Repeat for all other connectors (`pg-sink-lastdata.json`, `pg-sink-mutable.json`, `pg-sink-errors.json`, `mdb-sink.json`, `http-sink.json`).

> To confirm registration:

```bash
curl -H "Accept: application/json" http://localhost:8083/connectors
```

> To check connector status:

```bash
curl -s http://localhost:8083/connectors/your-connector/status | jq
```

---

## 🧪 Testing Sinks

You can verify data arrival using:

```bash
docker exec -it kafka /opt/kafka/bin/kafka-console-consumer.sh 
--bootstrap-server localhost:9092 
--topic YOUR_TOPIC_NAME 
--from-beginning --max-messages 10
```

Check tables in PostGIS or MongoDB after running the corresponding test input.
