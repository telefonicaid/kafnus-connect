/**
* Copyright 2026 Telefónica Soluciones de Informática y Comunicaciones de España, S.A.U.
*
* This file includes or is based on software originally developed by Confluent Inc.
* and has been modified by Telefónica Soluciones de Informática y Comunicaciones
* de España, S.A.U.
*
* Licensed under the Confluent Community License, Version 1.0.
* You may obtain a copy of the License at:
*
*   http://www.confluent.io/confluent-community-license
*
* This software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
* CONDITIONS OF ANY KIND, either express or implied.
*
* Authors:
*  - Álvaro Vega
*  - Gregorio Blázquez
*  - Fermín Galán
*  - Oriana Romero
*/

/**
 * Kafka Connect SMT that prepends a configurable prefix to MongoDB database
 * and collection names stored in the record key.
 *
 * The transformation expects schemaless JSON keys containing the fields
 * "database" and "collection", and rewrites them in-place before the record
 * is processed by the MongoDB Kafka Sink connector.
 *
 * This SMT is used to overcome the lack of dynamic namespace prefixing support
 * in the MongoDB Kafka Sink configuration, without requiring changes in
 * upstream producers.
 */

package com.telefonica;

import org.apache.kafka.common.config.ConfigDef;
import org.apache.kafka.common.config.ConfigException;
import org.apache.kafka.connect.connector.ConnectRecord;
import org.apache.kafka.connect.transforms.Transformation;
import org.apache.kafka.connect.transforms.util.SimpleConfig;

import java.util.HashMap;
import java.util.Map;

public class MongoNamespacePrefix<R extends ConnectRecord<R>> implements Transformation<R> {

    // === Config keys ===
    public static final String PREFIX_CONFIG = "prefix";

    private static final String DATABASE_FIELD = "database";
    private static final String COLLECTION_FIELD = "collection";

    private static final ConfigDef CONFIG_DEF = new ConfigDef()
        .define(
            PREFIX_CONFIG,
            ConfigDef.Type.STRING,
            ConfigDef.NO_DEFAULT_VALUE,
            ConfigDef.Importance.HIGH,
            "Prefix to prepend to MongoDB database and collection names"
        );

    // === Runtime config ===
    private String prefix;

    @Override
    public void configure(Map<String, ?> configs) {
        SimpleConfig config = new SimpleConfig(CONFIG_DEF, configs);
        this.prefix = config.getString(PREFIX_CONFIG);

        if (prefix == null || prefix.isEmpty()) {
            throw new ConfigException("MongoNamespacePrefix SMT requires a non-empty 'prefix' configuration");
        }
    }

    @Override
    @SuppressWarnings("unchecked")
    public R apply(R record) {

        if (record.key() == null) {
            return record;
        }

        if (!(record.key() instanceof Map)) {
            throw new ConfigException(
                "MongoNamespacePrefix SMT expects schemaless JSON key (Map<String, Object>)"
            );
        }

        Map<String, Object> key = (Map<String, Object>) record.key();

        Object dbObj = key.get(DATABASE_FIELD);
        Object collObj = key.get(COLLECTION_FIELD);

        if (dbObj == null || collObj == null) {
            // Nothing to do — let Mongo sink handle error policy
            return record;
        }

        String database = dbObj.toString();
        String collection = collObj.toString();

        boolean modified = false;

        if (!database.startsWith(prefix)) {
            database = prefix + database;
            modified = true;
        }

        if (!collection.startsWith(prefix)) {
            collection = prefix + collection;
            modified = true;
        }

        if (!modified) {
            return record;
        }

        // Create a shallow copy to avoid mutating original key
        Map<String, Object> newKey = new HashMap<>(key);
        newKey.put(DATABASE_FIELD, database);
        newKey.put(COLLECTION_FIELD, collection);

        return record.newRecord(
            record.topic(),
            record.kafkaPartition(),
            record.keySchema(),     // schemaless
            newKey,
            record.valueSchema(),
            record.value(),
            record.timestamp(),
            record.headers()
        );
    }

    @Override
    public ConfigDef config() {
        return CONFIG_DEF;
    }

    @Override
    public void close() {
        // Nothing to close
    }
}
