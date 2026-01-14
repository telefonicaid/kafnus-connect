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
 * Kafka Connect SMT (Single Message Transformation) that dynamically routes records
 * to SQL tables based on a configured SQL datamodel and NGSI metadata headers.
 *
 * The transformation computes the destination schema and table name at runtime,
 * rewrites the Kafka record topic to "schema.table", and relies on the JDBC Sink
 * connector to use ${topic} as the final table name.
 *
 * Unlike the previous approach based on a precomputed `target_table` header, this
 * SMT encapsulates all SQL datamodel logic internally. Upstream components only
 * provide base metadata (fiware-service, fiware-servicepath, entityType), and do
 * not need to be aware of the physical SQL layout.
 *
 * The SQL layout is selected using the `datamodel` configuration parameter.
 *
 * Supported datamodels:
 *
 * - dm-by-entity-type-database
 *     Schema: fiware-service
 *     Table : fiware-servicepath_entityType
 *
 * - dm-by-fixed-entity-type-database-schema
 *     Schema: fiware-servicepath
 *     Table : entityType
 *
 * Required headers (always expected from upstream producers):
 *
 * - fiware-service
 * - fiware-servicepath
 * - entityType
 * - entityId (currently unused, reserved for future datamodels)
 * - suffix (optional, added to table name if needed)
 *
 * Configuration:
 *
 * Minimal configuration:
 *
 *   transforms=HeaderRouter
 *   transforms.HeaderRouter.type=com.telefonica.HeaderRouter
 *   transforms.HeaderRouter.datamodel=dm-by-entity-type-database
 *
 * Optional overrides:
 *
 * - default.schema
 *     Forces a fixed schema for all records, overriding the datamodel.
 *
 * - headers.*
 *     Each logical value (service, servicepath, entitytype, entityid, suffix) can be
 *     resolved either from a header or from a fixed value:
 *
 *     * If not configured, the default header is used.
 *     * If configured and a header with that name exists, that header is used.
 *     * If configured and no such header exists, the configured value is used
 *       as a fixed literal.
 *
 * This allows mixing dynamic metadata with fixed values, enabling both
 * multi-tenant and single-tenant deployments with the same SMT.
 *
 * If a required value cannot be resolved for the selected datamodel, the SMT
 * throws a ConfigException and error handling is delegated to Kafka Connect.
 */

package com.telefonica;

import org.apache.kafka.common.config.ConfigDef;
import org.apache.kafka.common.config.ConfigException;
import org.apache.kafka.connect.connector.ConnectRecord;
import org.apache.kafka.connect.transforms.Transformation;
import org.apache.kafka.connect.transforms.util.SimpleConfig;
import org.apache.kafka.connect.header.Headers;

import java.util.Map;

public class HeaderRouter<R extends ConnectRecord<R>> implements Transformation<R> {

    // === Config keys ===
    public static final String DATAMODEL_CONFIG = "datamodel";
    public static final String DEFAULT_SCHEMA_CONFIG = "default.schema";

    public static final String HEADER_SERVICE_CONFIG = "headers.service";
    public static final String HEADER_SERVICEPATH_CONFIG = "headers.servicepath";
    public static final String HEADER_ENTITYTYPE_CONFIG = "headers.entitytype";
    public static final String HEADER_ENTITYID_CONFIG = "headers.entityid";
    public static final String HEADER_SUFFIX_CONFIG = "headers.suffix";
    public static final String FIXED_SUFFIX_CONFIG = "suffix";

    // === Datamodels ===
    public static final String DM_BY_ENTITY_TYPE_DATABASE = "dm-by-entity-type-database";
    public static final String DM_BY_FIXED_ENTITY_TYPE_DATABASE_SCHEMA = "dm-by-fixed-entity-type-database-schema";
    public static final String DM_POSTGIS_ERRORS = "dm-postgis-errors";

    private static final ConfigDef CONFIG_DEF = new ConfigDef()
        .define(DATAMODEL_CONFIG, ConfigDef.Type.STRING, ConfigDef.Importance.HIGH,
                "SQL datamodel used to build schema and table names")
        .define(DEFAULT_SCHEMA_CONFIG, ConfigDef.Type.STRING, null,
                ConfigDef.Importance.MEDIUM, "Fallback schema if none is resolved")
        .define(HEADER_SERVICE_CONFIG, ConfigDef.Type.STRING, null,
                ConfigDef.Importance.HIGH, "Service header name or fixed value")
        .define(HEADER_SERVICEPATH_CONFIG, ConfigDef.Type.STRING, null,
                ConfigDef.Importance.HIGH, "ServicePath header name or fixed value")
        .define(HEADER_ENTITYTYPE_CONFIG, ConfigDef.Type.STRING, null,
                ConfigDef.Importance.HIGH, "EntityType header name or fixed value")
        .define(HEADER_ENTITYID_CONFIG, ConfigDef.Type.STRING, null,
                ConfigDef.Importance.LOW, "EntityId header name or fixed value")
        .define(HEADER_SUFFIX_CONFIG, ConfigDef.Type.STRING, "suffix",
                ConfigDef.Importance.LOW, "Header containing flow/table suffix")
        .define(FIXED_SUFFIX_CONFIG, ConfigDef.Type.STRING, null,
                ConfigDef.Importance.LOW, "Fixed suffix to override header value if provided");

    // === Runtime config ===
    private String datamodel;
    private String defaultSchema;

    private String serviceHeader;
    private String servicePathHeader;
    private String entityTypeHeader;
    private String entityIdHeader;
    private String headerSuffix;
    private String fixedSuffix;

    private String resolveValue(Headers headers, String fixedValue, String headerName) {
        if (fixedValue != null) return fixedValue;

        return getHeaderValue(headers, headerName);
    }

    @Override
    public void configure(Map<String, ?> configs) {
        SimpleConfig config = new SimpleConfig(CONFIG_DEF, configs);
        this.datamodel = config.getString(DATAMODEL_CONFIG);
        this.defaultSchema = config.getString(DEFAULT_SCHEMA_CONFIG);

        this.serviceHeader = config.getString(HEADER_SERVICE_CONFIG);
        if (this.serviceHeader == null) this.serviceHeader = "fiware-service";
        this.servicePathHeader = config.getString(HEADER_SERVICEPATH_CONFIG);
        if (this.servicePathHeader == null) this.servicePathHeader = "fiware-servicepath";
        this.entityTypeHeader = config.getString(HEADER_ENTITYTYPE_CONFIG);
        if (this.entityTypeHeader == null) this.entityTypeHeader = "entityType";
        this.entityIdHeader = config.getString(HEADER_ENTITYID_CONFIG);
        if (this.entityIdHeader == null) this.entityIdHeader = "entityId";
        this.headerSuffix = config.getString(HEADER_SUFFIX_CONFIG);
        if (this.headerSuffix == null) this.headerSuffix = "suffix";
        this.fixedSuffix = config.getString(FIXED_SUFFIX_CONFIG);
    }

    @Override
    public R apply(R record) {
        Headers headers = record.headers();
        if (headers == null) return record;

        String service = resolveValue(headers, null, serviceHeader);
        String servicePath = resolveValue(headers, null, servicePathHeader);
        String entityType = resolveValue(headers, null, entityTypeHeader);

        String schema;
        String table;

        switch (datamodel) {
            case DM_BY_ENTITY_TYPE_DATABASE:
                schema = require(service, "fiware-service");
                table = require(servicePath, "fiware-servicepath") + "_" + require(entityType, "entityType");
                break;
            case DM_BY_FIXED_ENTITY_TYPE_DATABASE_SCHEMA:
                schema = require(servicePath, "fiware-servicepath");
                table = require(entityType, "entityType");
                break;
            case DM_POSTGIS_ERRORS:
                schema = require(service, "fiware-service");
                table = require(service, "fiware-service") + "_error_log";
                break;
            default:
                throw new ConfigException("Unsupported datamodel: " + datamodel);
        }

        // Resolver sufijo
        String suffix = resolveValue(headers, fixedSuffix, headerSuffix);
        if (suffix == null) suffix = "";
        table = table + suffix;

        if ((schema == null || schema.isEmpty()) && defaultSchema != null) {
            schema = defaultSchema;
        }

        if (schema == null || schema.isEmpty()) {
            throw new ConfigException("Schema could not be resolved for datamodel " + datamodel);
        }

        String newTopic = schema + "." + table;

        return record.newRecord(
            newTopic,
            record.kafkaPartition(),
            record.keySchema(),
            record.key(),
            record.valueSchema(),
            record.value(),
            record.timestamp(),
            headers
        );
    }

    private String getHeaderValue(Headers headers, String headerName) {
        if (headerName == null) return null;
        if (headers.lastWithName(headerName) == null) return null;
        Object value = headers.lastWithName(headerName).value();
        return value != null ? value.toString() : null;
    }

    private String require(String value, String name) {
        if (value == null || value.isEmpty()) {
            throw new ConfigException("Required header missing or empty: " + name);
        }
        return value;
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
