#!/bin/sh

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

set -e

CONFIG_FILE="/home/appuser/config/connect-distributed.properties"

cat > "${CONFIG_FILE}" <<EOF
bootstrap.servers=${CONNECT_BOOTSTRAP_SERVERS:-kafka:9092}
group.id=${CONNECT_GROUP_ID:-connect-cluster}

key.converter=${CONNECT_KEY_CONVERTER:-org.apache.kafka.connect.storage.StringConverter}
value.converter=${CONNECT_VALUE_CONVERTER:-org.apache.kafka.connect.json.JsonConverter}
value.converter.schemas.enable=${CONNECT_VALUE_CONVERTER_SCHEMAS_ENABLE:-true}

config.storage.topic=${CONNECT_CONFIG_STORAGE_TOPIC:-connect-configs}
offset.storage.topic=${CONNECT_OFFSET_STORAGE_TOPIC:-connect-offsets}
status.storage.topic=${CONNECT_STATUS_STORAGE_TOPIC:-connect-status}

config.storage.replication.factor=${CONNECT_CONFIG_STORAGE_REPLICATION_FACTOR:-1}
offset.storage.replication.factor=${CONNECT_OFFSET_STORAGE_REPLICATION_FACTOR:-1}
status.storage.replication.factor=${CONNECT_STATUS_STORAGE_REPLICATION_FACTOR:-1}

plugin.path=${CONNECT_PLUGIN_PATH:-/usr/local/share/kafnus-connect/plugins}

rest.port=${CONNECT_REST_PORT:-8083}
rest.advertised.host.name=${CONNECT_REST_ADVERTISED_HOST_NAME:-kafnus-connect}

config.providers=env
config.providers.env.class=org.apache.kafka.common.config.provider.EnvVarConfigProvider

# Security (optional)
if [ -n "${CONNECT_SECURITY_PROTOCOL}" ]; then
cat >> "${CONFIG_FILE}" <<EOF

security.protocol=${CONNECT_SECURITY_PROTOCOL}
sasl.mechanism=${CONNECT_SASL_MECHANISM}
sasl.jaas.config=${CONNECT_SASL_JAAS_CONFIG}

producer.security.protocol=${CONNECT_PRODUCER_SECURITY_PROTOCOL}
producer.sasl.mechanism=${CONNECT_PRODUCER_SASL_MECHANISM}
producer.sasl.jaas.config=${CONNECT_PRODUCER_SASL_JAAS_CONFIG}

consumer.security.protocol=${CONNECT_CONSUMER_SECURITY_PROTOCOL}
consumer.sasl.mechanism=${CONNECT_CONSUMER_SASL_MECHANISM}
consumer.sasl.jaas.config=${CONNECT_CONSUMER_SASL_JAAS_CONFIG}
EOF

echo ">> Starting Kafka Connect with config:"
cat "${CONFIG_FILE}"

exec "${KAFKA_HOME}/bin/connect-distributed.sh" "${CONFIG_FILE}"