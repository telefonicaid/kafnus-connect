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

FROM eclipse-temurin:17.0.19_10-jdk-jammy

ARG KAFKA_VERSION=4.3.1
ARG SCALA_VERSION=2.13
ENV KAFKA_HOME=/opt/kafka
ENV CONNECT_PLUGIN_PATH=/usr/local/share/kafnus-connect/plugins

## -----------------------------
## Build tools
## -----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git tar gzip maven ca-certificates wget unzip gnupg2 \
    && rm -rf /var/lib/apt/lists/*

## -----------------------------
## Download Kafka (official distribution)
## -----------------------------
RUN mkdir -p /tmp/kafka_extract && \
    curl -fsSL \
    "https://downloads.apache.org/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz" \
-o /tmp/kafka.tgz && \
    tar -xzf /tmp/kafka.tgz -C /tmp/kafka_extract && \
    mv /tmp/kafka_extract/kafka_${SCALA_VERSION}-${KAFKA_VERSION} /opt/ && \
    ln -s /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION} ${KAFKA_HOME} && \
    rm /tmp/kafka.tgz

## -----------------------------
## Plugin directories
## -----------------------------
RUN mkdir -p ${CONNECT_PLUGIN_PATH}

## -----------------------------
## Non-root user
## -----------------------------
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser && \
    chown -R appuser:appuser ${KAFKA_HOME} ${CONNECT_PLUGIN_PATH}
USER appuser
WORKDIR ${KAFKA_HOME}

## -----------------------------
## Custom SMTs: HeaderRouter and MongoNamespacePrefix
## -----------------------------
USER root
COPY src/kafnus-connect-smt /usr/local/build/kafnus-connect-smt
RUN cd /usr/local/build/kafnus-connect-smt && \
    mvn clean package -DskipTests && \
    mkdir -p ${CONNECT_PLUGIN_PATH}/kafnus-connect-smt && \
    cp target/kafnus-connect-smt-1.1.0-jar-with-dependencies.jar \
       ${CONNECT_PLUGIN_PATH}/kafnus-connect-smt/kafnus-connect-smt-1.1.0.jar && \
    rm -rf /usr/local/build/kafnus-connect-smt
USER appuser

## -----------------------------
## Connectors
## -----------------------------

## JDBC Connector (PostGIS fork)
RUN cd /tmp && \
    git clone https://github.com/telefonicaid/kafka-connect-jdbc-postgis.git && \
    cd kafka-connect-jdbc-postgis && \
    git checkout task/upgrade_10_9_7 || true && \
    mvn clean package -DskipTests -Dcheckstyle.skip=true && \
    mkdir -p ${CONNECT_PLUGIN_PATH}/kafka-connect-jdbc && \
    cp target/kafka-connect-jdbc-10.9.7.jar ${CONNECT_PLUGIN_PATH}/kafka-connect-jdbc/ && \
    rm -rf /tmp/kafka-connect-jdbc-postgis

## PostgreSQL JDBC Driver
RUN curl -fsSL https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.9/postgresql-42.7.12.jar \
    -o ${CONNECT_PLUGIN_PATH}/kafka-connect-jdbc/postgresql-42.7.12.jar

## MongoDB Kafka Connector (MongoDB official version - full jar)
RUN mkdir -p ${CONNECT_PLUGIN_PATH}/mongodb && \
    curl -fsSL https://repo1.maven.org/maven2/org/mongodb/kafka/mongo-kafka-connect/2.1.0/mongo-kafka-connect-2.1.0-all.jar \
      -o ${CONNECT_PLUGIN_PATH}/mongodb/mongo-kafka-connect-2.1.0-all.jar

## HTTP Connector (telefonicaid fork)
RUN cd /tmp && \
    git clone https://github.com/telefonicaid/http-connector-for-apache-kafka-graphql.git && \
    cd http-connector-for-apache-kafka-graphql && \
    git checkout version0.9.0_basicv3 || true && \
    ./gradlew clean distTar && \
    mkdir -p ${CONNECT_PLUGIN_PATH}/http-connector && \
    tar xfv build/distributions/http-connector-for-apache-kafka-0.9.0.tar -C ${CONNECT_PLUGIN_PATH}/http-connector --strip-components=1 && \
    rm -rf /tmp/http-connector-for-apache-kafka-graphql

## -----------------------------
## JMX Exporter
## -----------------------------
RUN mkdir -p /home/appuser/jmx_exporter && \
    curl -fsSL https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.20.0/jmx_prometheus_javaagent-0.20.0.jar \
      -o /home/appuser/jmx_exporter/jmx_prometheus_javaagent.jar

## -----------------------------
## Config directory for Kafka Connect
## -----------------------------
RUN mkdir -p /home/appuser/config

## Fix Java 17 + cgroups v2 issue
ENV JAVA_TOOL_OPTIONS="-XX:+UnlockExperimentalVMOptions -XX:-UseContainerSupport"

## -----------------------------
## Entrypoint
## -----------------------------
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

ENV PATH="${KAFKA_HOME}/bin:${PATH}"
ENV KAFKA_JMX_PORT=9100
ENV JMX_PROMETHEUS_PORT=9100

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["connect-distributed", "/home/appuser/config/connect-distributed.properties"]

