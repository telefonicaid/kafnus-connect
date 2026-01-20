/**
 * Copyright 2025 Telefónica Soluciones de Informática y Comunicaciones de España, S.A.U.
 * PROJECT: openmetadata-scripts
 *
 * This software and / or computer program has been developed by Telefónica Soluciones
 * de Informática y Comunicaciones de España, S.A.U (hereinafter TSOL) and is protected
 * as copyright by the applicable legislation on intellectual property.
 *
 * It belongs to TSOL, and / or its licensors, the exclusive rights of reproduction,
 * distribution, public communication and transformation, and any economic right on it,
 * all without prejudice of the moral rights of the authors mentioned above. It is expressly
 * forbidden to decompile, disassemble, reverse engineer, sublicense or otherwise transmit
 * by any means, translate or create derivative works of the software and / or computer
 * programs, and perform with respect to all or part of such programs, any type of exploitation.
 *
 * Any use of all or part of the software and / or computer program will require the
 * express written consent of TSOL. In all cases, it will be necessary to make
 * an express reference to TSOL ownership in the software and / or computer
 * program.
 *
 * Non-fulfillment of the provisions set forth herein and, in general, any violation of
 * the peaceful possession and ownership of these rights will be prosecuted by the means
 * provided in both Spanish and international law. TSOL reserves any civil or
 * criminal actions it may exercise to protect its rights.
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
