![FIWARE Incubating](https://fiware.github.io/catalogue/badges/statuses/status-incubating.svg)

# 🛰️ Kafnus Connect

**Kafnus Connect** is the persistence layer of the [Kafnus](https://github.com/telefonicaid/kafnus) ecosystem — a modern, Kafka-based replacement for **Cygnus** in FIWARE smart city environments.

It provides ready-to-use **Kafka Connect** images with custom Single Message Transforms (SMTs) and pre-integrated sink connectors for **PostGIS**, **MongoDB**, and **HTTP endpoints**.

This project is part of [FIWARE](https://www.fiware.org/). For more information
check the FIWARE Catalogue entry for the
[Core Context Management](https://github.com/Fiware/catalogue/tree/master/core).

| :whale: [Docker Hub](https://hub.docker.com/r/telefonicaiot/kafnus-connect) |
|---|

---

## ⚙️ Overview

Kafnus Connect consumes processed NGSI events from Kafka topics (produced by [Kafnus NGSI](https://github.com/telefonicaid/kafnus)) and persists them into target datastores or APIs.

### Supported sinks

- 🗺️ **PostGIS (via custom JDBC connector)**
  - Forked and extended to handle GeoJSON geometries and NGSI-specific data structures.
- 📦 **MongoDB**
  - Official MongoDB Kafka connector for JSON document storage.
- 🌐 **HTTP**
  - [Aiven Open HTTP Connector](https://github.com/Aiven-Open/http-connector-for-apache-kafka) for forwarding events to REST endpoints.
  - Forked to handle 200 responses with errors

---

## 🧱 Architecture

```
Kafka (processed topics)
       │
  Header Router (datamodels)
       │ 
       ▼
  Kafnus Connect (Kafka Connect)
   ├─ JDBC Sink (PostGIS)
   ├─ MongoDB Sink
   └─ HTTP Sink
```

The HeaderRouter SMT is responsible for dynamically resolving the destination
**database schema and table name** at runtime based on NGSI headers and a
configurable SQL datamodel, removing any SQL layout logic from upstream producers.

Each connector can be independently configured via environment variables or `connect-distributed.properties`.  
Custom SMTs can be chained to transform headers or message formats before persistence.

---

## 🚀 Usage

### Build locally

```bash
docker build -t telefonicaiot/kafnus-connect:latest .
```

### Run example

```bash
docker run -d   --name kafnus-connect   -e CONNECT_BOOTSTRAP_SERVERS=kafka:9092   -e CONNECT_GROUP_ID=kafnus-connect   -e CONNECT_CONFIG_STORAGE_TOPIC=connect-configs   -e CONNECT_OFFSET_STORAGE_TOPIC=connect-offsets   -e CONNECT_STATUS_STORAGE_TOPIC=connect-status   telefonicaiot/kafnus-connect:latest
```

> For complete examples, see the [`tests_end2end`](https://github.com/telefonicaid/kafnus/tree/main/tests_end2end) folder in the main Kafnus repository.

---

## 🧪 Testing

Integration and end-to-end testing are performed from the [Kafnus NGSI](https://github.com/telefonicaid/kafnus) repository, where complete data flow scenarios are executed using **Testcontainers**.

This repository also includes his own python tests (similar to Kafnus tests) and unit tests for the custom Java SMTs in [src/kafnus-connect-smt/src/test/java](src/kafnus-connect-smt/src/test/java), executed with Maven and JUnit 5.

Coverage is generated with JaCoCo for this SMT module and published to Coveralls from CI. This coverage reflects SMT unit tests (Java), while functional validation of the complete pipeline remains in the Python E2E suite.

---

## 🧰 Configuration & Extensions

- Custom SMTs are available in `src/kafnus-connect-smt/` covering JDBC and MongoDB sinks:
  - `HeaderRouter`: dynamic SQL routing for JDBC (schema/table resolution)
  - `MongoNamespacePrefix`: MongoDB database/collection prefixing
- New sinks can be added by extending the base image and adding plugins under `/usr/share/java/`.
- Monitoring via **Prometheus JMX Exporter** is supported out of the box.

For deeper technical details about how Kafnus Connect is configured, built, and extended — including:

- Environment setup and logging configuration
- Plugin management and sink registration
- Supported sinks and custom SMTs
- Usage of EnvVarConfigProvider for connector configuration

👉 See [Technical Configuration Guide](./doc/technical_configuration.md)

---

## 📚 Documentation

- [Kafnus ecosystem overview](https://github.com/telefonicaid/kafnus/blob/main/doc/00_overview.md)
- [PostGIS connector fork](https://github.com/telefonicaid/kafka-connect-jdbc-postgis)
- [MongoDB connector docs](https://www.mongodb.com/docs/kafka-connector/current/)
- [Aiven HTTP Connector](https://github.com/Aiven-Open/http-connector-for-apache-kafka)
- [Aiven HTTP Connector forked](https://github.com/telefonicaid/http-connector-for-apache-kafka-graphql)

---

> 🧭 **Project structure note**
>
> This repository is part of the [Kafnus ecosystem](https://github.com/telefonicaid/kafnus):
> - [Kafnus NGSI (processing)](https://github.com/telefonicaid/kafnus)
> - [Kafnus Connect (persistence)](https://github.com/telefonicaid/kafnus-connect)

---

## 👥 Contributors

The list of contributors to the Kafnus-Connect project can be found in
[`CONTRIBUTORS.md`](./CONTRIBUTORS.md).