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

---

### 4. Custom SMTs

Path: `src/kafnus-connect-smt/`

Kafnus includes a suite of custom Kafka Connect **Single Message Transforms (SMTs)** that encapsulate connector-specific routing and namespace resolution logic, keeping persistence configuration entirely within Kafka Connect and independent from upstream producers.

---

#### **4.1 HeaderRouter (JDBC Sink)**

`HeaderRouter` is a custom Kafka Connect **Single Message Transform (SMT)** that dynamically computes the **destination schema and table name** for JDBC sink connectors based on NGSI metadata and a configurable SQL datamodel.

This SMT centralizes all SQL routing logic inside Kafka Connect, removing the need for upstream components to precompute physical table names.

##### 🔧 Core Configuration

Minimal required configuration:

```json
"transforms": "HeaderRouter",
"transforms.HeaderRouter.type": "com.telefonica.HeaderRouter",
"transforms.HeaderRouter.datamodel": "dm-by-entity-type-database"
```

The resolved destination is written to the Kafka Connect topic name, allowing standard JDBC Sink configuration using:

```json
"table.name.format": "${topic}"
```

---

##### 🧩 Supported SQL Datamodels

###### `dm-by-entity-type-database`

| Element | Value                           |
| ------- | ------------------------------- |
| Schema  | `fiware-service`                |
| Table   | `fiware-servicepath_entityType` |

---

###### `dm-by-fixed-entity-type-database-schema`

| Element | Value                |
| ------- | -------------------- |
| Schema  | `fiware-servicepath` |
| Table   | `entityType`         |

---

###### `dm-postgis-errors`

| Element | Value                        |
| ------- | ---------------------------- |
| Schema  | `fiware-service`             |
| Table   | `<fiware-service>_error_log` |

This datamodel is intended for JDBC sinks consuming error or DLQ topics.

###### `dm-http-errors`

| Element | Value                        |
| ------- | ---------------------------- |
| Schema  | `fiware-service`             |
| Table   | `<fiware-service>_error_log` |

This datamodel may evolve and is used specifically for HTTP error flows. Currently, it is designed to override the schema using `"transforms.HeaderRouter.headers.schema": "<SCHEMA>"`.

##### 🧠 Header Resolution Logic (Dynamic vs Fixed)

Each logical value used by the datamodel can be resolved flexibly.

Supported logical fields:

* service
* servicepath
* entitytype
* entityid
* suffix

For each field:

1. If the configuration value matches an existing Kafka header → header value is used
2. If no such header exists → the configuration value is treated as a **fixed literal**
3. If no configuration is provided → default NGSI headers are used

Default NGSI header names:

| Logical field | Default header       |
| ------------- | -------------------- |
| service       | `fiware-service`     |
| servicepath   | `fiware-servicepath` |
| entitytype    | `entityType`         |
| entityid      | `entityId`           |
| suffix        | `suffix`             |
| schema        | `schema`             |

This allows mixing **multi-tenant dynamic routing** with **static single-tenant deployments**.

##### ➕ Optional Table Suffix

A suffix can be appended to the resolved table name:

* Dynamically via a Kafka header (`suffix` by default)
* Or statically via configuration

Configuration example:

```json
"transforms.HeaderRouter.suffix": "_historic"
```

If neither a header nor a fixed value is present, the suffix safely defaults to an empty string.

##### 🧭 Schema Override (`headers.schema`)

The `headers.schema` parameter acts as a **hard override** for the resolved schema.

**Behavior:**

* If `headers.schema` is configured → it is **always used as the destination schema**
* If not configured → the schema resolved by the selected datamodel is used

Example:

```json
"transforms.HeaderRouter.datamodel": "dm-postgis-errors",
"transforms.HeaderRouter.headers.schema": "test"
```

Resulting destination:

```
test.<fiware-service>_error_log
```

This is especially useful in test environments or deployments where the physical database schema must remain fixed.

##### ⚠️ Validation & Errors

* Required values are validated per datamodel
* Missing mandatory metadata results in clear `ConfigException`s
* Error handling and retries are delegated to Kafka Connect mechanisms (DLQ, retries, task failure)

---

#### **4.2 MongoNamespacePrefix (MongoDB Sink)**

`MongoNamespacePrefix` is a custom Kafka Connect **Single Message Transform (SMT)** that handles **configurable MongoDB database and collection name prefixing**.

##### Background & Rationale

In kafnus, MongoDB database and collection names are dynamically resolved at runtime. However, the **MongoDB Kafka Sink connector does not support string composition** (e.g., `prefix + field`) via configuration alone. Namespace mapping (`FieldPathNamespaceMapper`) can only use **field values as-is**.

Because of this limitation, any logic related to **prefixing database or collection names** must be handled **before the record reaches the MongoDB Sink connector**, in the same way that SQL routing is handled for JDBC sinks via `HeaderRouter`.

##### Purpose

`MongoNamespacePrefix`:

* Reads the MongoDB **database** and **collection** names from Kafka record headers
* Prepends a configurable prefix to each
* Writes the resulting values back to the same headers
* Leaves the Kafka topic unchanged

This allows the MongoDB Sink connector to continue using:

```properties
namespace.mapper = FieldPathNamespaceMapper
namespace.mapper.key.database.field = database
namespace.mapper.key.collection.field = collection
```

while receiving **final, fully-resolved namespace values** with prefixes applied.

##### Core Configuration

Minimal required configuration:

```json
"transforms": "MongoPrefix",
"transforms.MongoPrefix.type": "com.telefonica.MongoNamespacePrefix",
"transforms.MongoPrefix.database.prefix": "my_prefix_",
"transforms.MongoPrefix.collection.prefix": "my_prefix_"
```

Optional header customization (uses NGSI defaults if not specified):

```json
"transforms.MongoPrefix.headers.database": "database",
"transforms.MongoPrefix.headers.collection": "collection"
```

##### Architecture Alignment

Both `HeaderRouter` (JDBC) and `MongoNamespacePrefix` (MongoDB) follow the **same architectural principle**:

| Aspect               | HeaderRouter (JDBC)                              | MongoNamespacePrefix (MongoDB)               |
| -------------------- | ------------------------------------------------ | -------------------------------------------- |
| Connector limitation  | JDBC needs fixed topic → table mapping           | Mongo Sink cannot compose namespace strings  |
| Where logic lives    | Kafka Connect SMT                                | Kafka Connect SMT                            |
| Input                | NGSI headers (service, servicepath, entitytype) | MongoDB namespace headers                    |
| Output               | Physical SQL destination (schema.table)          | Physical MongoDB namespace                   |
| Upstream awareness   | Not required                                     | Not required                                 |

This keeps **all physical persistence logic inside Kafka Connect** and ensures consistent behavior across JDBC and MongoDB sinks.

##### Validation & Errors

* Required namespace values are validated at SMT initialization
* Missing headers results in clear `ConfigException`s
* Prefix configuration is optional; if omitted, the original headers are passed through unchanged
* Error handling and retries are delegated to Kafka Connect mechanisms

---

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

## 🔁 Retry & Failure Handling Configuration

Kafnus Connect sink connectors use a combination of **error-handling parameters** and **connection retry settings** to determine how they behave when SQL operations fail or when the database becomes temporarily unavailable.

### ⚠️ SQL-Level Errors → No Retries (Direct DLQ)

The JDBC sink is configured **not to retry** SQL processing errors such as:

* missing tables or schema mismatch,
* invalid column types,
* malformed SQL statements.

This behavior is controlled by:

```json
"errors.tolerance": "all",
"errors.deadletterqueue.topic.name": "smc_raw_errors",
"errors.deadletterqueue.context.headers.enable": "true",
"errors.deadletterqueue.topic.replication.factor": "1",
"errors.log.enable": "true",
"errors.log.include.messages": "true",
"max.retries": "0",
"retry.backoff.ms": "0"
```

With `max.retries = 0`, **SQL write failures are not retried at all**.
Instead, the failing record is immediately published to the **Dead Letter Queue (DLQ)** topic (`smc_raw_errors`), where it will later be inserted into the PostGIS *errors* table by the dedicated DLQ sink.

This ensures that structural or schema-related issues do not stall the connector.

---

### 🔌 Database Connectivity Errors → Limited Retries

Connectivity-related failures (e.g., database down, network outage) are handled separately through the following parameters:

```json
"connection.attempts": "10",
"connection.backoff.ms": "10000"
```

This means:

* The connector will try to re-establish the JDBC connection **10 times**.
* The time between retries is **10 seconds**.
* The maximum recovery window is therefore approximately:

```
10 attempts × 10 seconds = ~100 seconds total
```

If the database remains unavailable **longer than this time window**, the sink **task transitions to `FAILED` state**.

### ❗ Important Limitation: Tasks Do NOT Auto-Recover

Kafka Connect **does not automatically restart FAILED tasks**, even when the database becomes available again.

This behavior is confirmed and discussed in:

* **Related Issue:** [https://github.com/telefonicaid/kafnus-connect/issues/10](https://github.com/telefonicaid/kafnus-connect/issues/10)
* **PR / Test Discussion (DB Outage Recovery):** internal Kafnus Connect PR referenced in Issue #10

In this scenario:

* The **connector** remains in `RUNNING` state (misleading).
* The **task** enters `FAILED` state.
* The task **never restarts automatically**, and data ingestion stops silently.

This is a known limitation of Kafka Connect and the JDBC Sink connector.

---

### 📝 Summary

| Failure Type                                     | Retried?                    | Outcome                                                      |
| ------------------------------------------------ | --------------------------- | ------------------------------------------------------------ |
| **SQL errors** (missing table, bad schema, etc.) | ❌ No                        | Record sent to `smc_raw_errors` DLQ immediately                  |
| **DB connectivity < 100s outage**                | ✅ Yes                       | Connector recovers normally                                  |
| **DB connectivity > 100s outage**                | ❌ No (exceeds retry window) | Task enters `FAILED` and stays down until manually restarted |

---

### 📌 Why This Matters

Due to the retry window defined by:

```
connection.attempts × connection.backoff.ms
```

any outage exceeding this threshold results in a **permanent stoppage of data persistence** unless manually mitigated.

This behavior is a key part of the design discussion in the Kafnus Connect Issues & PRs and is addressed by the resilience tests added in the project.

---

## 📦 JDBC Sink Batch Processing Configuration

Kafnus Connect relies on the **Confluent JDBC Sink Connector** for persisting NGSI data into PostGIS.
By default, this connector uses **Prepared Statements** and **internal batching mechanics** to efficiently insert records in bulk.

Batching behavior is a critical aspect of performance and resilience under high-throughput scenarios and is explicitly validated by the batching tests (`test_jdbc_batch_backlog.py`, `test_jdbc_batch_errors.py`) in [Kafnus tests](https://github.com/telefonicaid/kafnus).

---

### 🔢 `batch.size`

The most important parameter controlling JDBC batch behavior is:

```json
"batch.size": "3000"
```

**Definition**
Specifies the maximum number of records the JDBC sink will attempt to batch together into a single database insert operation, when possible.

**Properties:**

| Property    | Value   |
| ----------- | ------- |
| Type        | `int`   |
| Default     | `3000`  |
| Valid Range | `0 … ∞` |
| Importance  | Medium  |

**Behavior:**

* Records are accumulated in memory until `batch.size` is reached
* The batch is then flushed as a single JDBC operation
* If fewer records are available, a smaller batch is flushed
* Setting `batch.size = 0` disables batching entirely (not recommended)

---

### ⚠️ Interaction with Kafka Consumer Polling

A critical (and often overlooked) detail is that **batching is constrained by Kafka consumer polling**.

> ❗ If the Kafka consumer retrieves fewer records than `batch.size`, the effective batch size is reduced.

This means:

```text
effective_batch_size = min(batch.size, consumer.max.poll.records)
```

If:

```json
batch.size = 3000
consumer.max.poll.records = 500
```

➡️ **Batching will never exceed 500 records**, even though `batch.size` is higher.

---

### 🔧 Configuring `consumer.max.poll.records`

Kafka Connect workers define a global default for consumer polling:

```properties
consumer.max.poll.records
```

If this value is **lower than `batch.size`**, full batching will be lost.

To override this **per connector**, the JDBC sink supports:

```json
"consumer.override.max.poll.records": "3000"
```

This ensures that the connector can actually retrieve enough records in a single poll to form a full batch.

**Recommended configuration pattern:**

```json
"batch.size": "3000",
"consumer.override.max.poll.records": "3000"
```

This configuration guarantees that batching behaves as intended.

---

### 🧪 Relation to Batching Tests

The batching tests included in this project (`test_jdbc_batch_backlog.py` and `test_jdbc_batch_errors.py`) are explicitly designed to validate this behavior:

* A backlog significantly larger than `batch.size` is accumulated while services are stopped
* When Kafnus Connect starts:

  * Records are consumed in chunks
  * JDBC inserts are executed in batches
  * Processing continues until a **sentinel entity** is observed
* Mixed batches containing **valid and invalid records** are handled gracefully:

  * Valid rows are persisted
  * Invalid rows are routed to the DLQ
  * Batch processing continues without stalling

These tests implicitly confirm that:

* JDBC batching is enabled and effective
* Partial failures inside a batch do not block progress
* Batch size configuration is compatible with Kafka consumer settings

---

### 📈 Performance Considerations

Choosing an appropriate `batch.size` involves trade-offs:

| Batch Size | Effect                                        |
| ---------- | --------------------------------------------- |
| Too small  | Increased JDBC overhead, lower throughput     |
| Too large  | Higher memory usage, longer transaction times |
| Balanced   | Optimal throughput and stability              |

For PostGIS sinks, a batch size of **3000** has proven to be a good default under typical workloads and is used consistently across tests.

---

### 📝 Summary

| Aspect           | Recommendation                                             |
| ---------------- | ---------------------------------------------------------- |
| Enable batching  | Use default JDBC behavior                                  |
| Batch size       | `3000` (default)                                           |
| Consumer polling | Match `consumer.override.max.poll.records` to `batch.size` |
| Error handling   | Combine batching with DLQ (`errors.tolerance=all`)         |
| Validation       | Covered by batching and error-injection tests              |

---

### 🔗 References

* Confluent JDBC Sink – Overview
  [https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html)
* Confluent JDBC Sink – Configuration Options
  [https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html)

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
