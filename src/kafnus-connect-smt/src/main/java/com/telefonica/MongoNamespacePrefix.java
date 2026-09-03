/*
* Copyright 2026 Telefónica Soluciones de Informática y Comunicaciones de España, S.A.U.
*
* This file is part of kafnus-connect
*
* kafnus-connect is free software: you can redistribute it and/or
* modify it under the terms of the GNU Affero General Public License as
* published by the Free Software Foundation, either version 3 of the
* License, or (at your option) any later version.
*
* kafnus-connect is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
* General Public License for more details.
*
* You should have received a copy of the GNU Affero General Public License
* along with kafnus. If not, see http://www.gnu.org/licenses/.
*/

/**
 * Kafka Connect SMT that prepends configurable prefixes to MongoDB database
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
    public static final String DATABASE_PREFIX_CONFIG = "dbname.prefix";
    public static final String COLLECTION_PREFIX_CONFIG = "collection.prefix";

    private static final String DATABASE_FIELD = "database";
    private static final String COLLECTION_FIELD = "collection";

    private static final ConfigDef CONFIG_DEF = new ConfigDef()
        .define(
            PREFIX_CONFIG,
            ConfigDef.Type.STRING,
            "",
            ConfigDef.Importance.MEDIUM,
            "Legacy shared prefix to prepend to MongoDB database and collection names"
        )
        .define(
            DATABASE_PREFIX_CONFIG,
            ConfigDef.Type.STRING,
            "",
            ConfigDef.Importance.HIGH,
            "Prefix to prepend to the MongoDB database name"
        )
        .define(
            COLLECTION_PREFIX_CONFIG,
            ConfigDef.Type.STRING,
            "",
            ConfigDef.Importance.HIGH,
            "Prefix to prepend to the MongoDB collection name"
        );

    // === Runtime config ===
    private String databasePrefix;
    private String collectionPrefix;

    @Override
    public void configure(Map<String, ?> configs) {
        SimpleConfig config = new SimpleConfig(CONFIG_DEF, configs);

        String sharedPrefix = normalizePrefix(config.getString(PREFIX_CONFIG));
        this.databasePrefix = firstNonEmpty(
            normalizePrefix(config.getString(DATABASE_PREFIX_CONFIG)),
            sharedPrefix
        );
        this.collectionPrefix = firstNonEmpty(
            normalizePrefix(config.getString(COLLECTION_PREFIX_CONFIG)),
            sharedPrefix
        );

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

        if (!database.startsWith(databasePrefix)) {
            database = databasePrefix + database;
            modified = true;
        }

        if (!collection.startsWith(collectionPrefix)) {
            collection = collectionPrefix + collection;
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

    private static String normalizePrefix(String prefix) {
        if (prefix == null) {
            return "";
        }

        return prefix.trim();
    }

    private static String firstNonEmpty(String primary, String fallback) {
        return primary.isEmpty() ? fallback : primary;
    }
}
