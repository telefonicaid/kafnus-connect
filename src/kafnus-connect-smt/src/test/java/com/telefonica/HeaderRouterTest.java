package com.telefonica;

import org.apache.kafka.common.config.ConfigException;
import org.apache.kafka.connect.sink.SinkRecord;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class HeaderRouterTest {

    @Test
    void shouldUseConfiguredDatamodelWhenHeaderIsMissing() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database-schema");

        SinkRecord out = router.apply(newRecord(baseHeaders()));

        assertEquals("simple.simple_sensor", out.topic());
    }

    @Test
    void shouldUseHeaderDatamodelSchemaWhenPresent() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database");

        Map<String, String> headers = baseHeaders();
        headers.put("fiware-datamodel", "dm-by-entity-type-database-schema");

        SinkRecord out = router.apply(newRecord(headers));

        assertEquals("simple.simple_sensor", out.topic());
    }

    @Test
    void shouldUseHeaderDatamodelDatabaseWhenPresent() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database-schema");

        Map<String, String> headers = baseHeaders();
        headers.put("fiware-datamodel", "dm-by-entity-type-database");

        SinkRecord out = router.apply(newRecord(headers));

        assertEquals("test.simple_sensor", out.topic());
    }

    @Test
    void shouldFallbackToConfiguredDatamodelWhenHeaderIsEmpty() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database-schema");

        Map<String, String> headers = baseHeaders();
        headers.put("fiware-datamodel", "");

        SinkRecord out = router.apply(newRecord(headers));

        assertEquals("simple.simple_sensor", out.topic());
    }

    @Test
    void shouldUseDefaultDatamodelWhenHeaderAndConfigAreMissing() {
        HeaderRouter<SinkRecord> router = newRouter(null);

        SinkRecord out = router.apply(newRecord(baseHeaders()));

        assertEquals("test.simple_sensor", out.topic());
    }

    @Test
    void shouldFailWhenHeaderDatamodelIsInvalid() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database-schema");

        Map<String, String> headers = baseHeaders();
        headers.put("fiware-datamodel", "dm-not-supported");

        assertThrows(ConfigException.class, () -> router.apply(newRecord(headers)));
    }

    @Test
    void shouldFallbackToConfiguredDatamodelWhenHeaderIsBlank() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database-schema");

        Map<String, String> headers = baseHeaders();
        headers.put("fiware-datamodel", "   ");

        SinkRecord out = router.apply(newRecord(headers));

        assertEquals("simple.simple_sensor", out.topic());
    }

    @Test
    void shouldUseDefaultDatamodelWhenConfiguredDatamodelIsBlank() {
        HeaderRouter<SinkRecord> router = newRouter("   ");

        SinkRecord out = router.apply(newRecord(baseHeaders()));

        assertEquals("test.simple_sensor", out.topic());
    }

    @Test
    void shouldFailWhenConfiguredDatamodelIsInvalid() {
        HeaderRouter<SinkRecord> router = newRouter("dm-not-supported");

        assertThrows(ConfigException.class, () -> router.apply(newRecord(baseHeaders())));
    }

    // === Datamodels ===

    @Test
    void shouldRouteFixedEntityTypeDatabaseSchema() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-fixed-entity-type-database-schema");

        SinkRecord out = router.apply(newRecord(baseHeaders()));

        assertEquals("simple.sensor", out.topic());
    }

    @Test
    void shouldRoutePostgisErrorsToServiceErrorLog() {
        HeaderRouter<SinkRecord> router = newRouter("dm-postgis-errors");

        SinkRecord out = router.apply(newRecord(baseHeaders()));

        assertEquals("test.test_error_log", out.topic());
    }

    @Test
    void shouldRouteHttpErrorsToServiceErrorLog() {
        HeaderRouter<SinkRecord> router = newRouter("dm-http-errors");

        SinkRecord out = router.apply(newRecord(baseHeaders()));

        assertEquals("test.test_error_log", out.topic());
    }

    @Test
    void shouldAllowEmptyServicePathInEntityTypeDatabase() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database");

        Map<String, String> headers = baseHeaders();
        headers.put("fiware-servicepath", "");

        SinkRecord out = router.apply(newRecord(headers));

        assertEquals("test._sensor", out.topic());
    }

    @Test
    void shouldFailWhenServicePathIsEmptyInEntityTypeDatabaseSchema() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database-schema");

        Map<String, String> headers = baseHeaders();
        headers.put("fiware-servicepath", "");

        assertThrows(ConfigException.class, () -> router.apply(newRecord(headers)));
    }

    @Test
    void shouldFailWhenServicePathIsEmptyInFixedEntityTypeDatabaseSchema() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-fixed-entity-type-database-schema");

        Map<String, String> headers = baseHeaders();
        headers.put("fiware-servicepath", "");

        assertThrows(ConfigException.class, () -> router.apply(newRecord(headers)));
    }

    @Test
    void shouldFailWhenEntityTypeIsEmpty() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database");

        Map<String, String> headers = baseHeaders();
        headers.put("entityType", "");

        assertThrows(ConfigException.class, () -> router.apply(newRecord(headers)));
    }

    @Test
    void shouldFailWhenServiceHeaderHasNullValue() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database");

        Map<String, String> headers = baseHeaders();
        headers.put("fiware-service", null);

        assertThrows(ConfigException.class, () -> router.apply(newRecord(headers)));
    }

    // === Suffix ===

    @Test
    void shouldAppendSuffixHeaderToTable() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database");

        Map<String, String> headers = baseHeaders();
        headers.put("suffix", "_lastdata");

        SinkRecord out = router.apply(newRecord(headers));

        assertEquals("test.simple_sensor_lastdata", out.topic());
    }

    @Test
    void shouldIgnoreMissingSuffixHeader() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database");

        Map<String, String> headers = baseHeaders();
        headers.remove("suffix");

        SinkRecord out = router.apply(newRecord(headers));

        assertEquals("test.simple_sensor", out.topic());
    }

    @Test
    void shouldIgnoreSuffixHeaderWithNullValue() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database");

        Map<String, String> headers = baseHeaders();
        headers.put("suffix", null);

        SinkRecord out = router.apply(newRecord(headers));

        assertEquals("test.simple_sensor", out.topic());
    }

    @Test
    void shouldPreferFixedSuffixOverHeader() {
        Map<String, String> cfg = new HashMap<>();
        cfg.put("suffix", "_mutable");
        HeaderRouter<SinkRecord> router = newRouterWithConfig(cfg);

        Map<String, String> headers = baseHeaders();
        headers.put("suffix", "_lastdata");

        SinkRecord out = router.apply(newRecord(headers));

        assertEquals("test.simple_sensor_mutable", out.topic());
    }

    // === Overrides ===

    @Test
    void shouldOverrideSchemaWhenHeadersSchemaIsConfigured() {
        Map<String, String> cfg = new HashMap<>();
        cfg.put("headers.schema", "custom");
        HeaderRouter<SinkRecord> router = newRouterWithConfig(cfg);

        SinkRecord out = router.apply(newRecord(baseHeaders()));

        assertEquals("custom.simple_sensor", out.topic());
    }

    @Test
    void shouldIgnoreEmptyHeadersSchema() {
        Map<String, String> cfg = new HashMap<>();
        cfg.put("headers.schema", "");
        HeaderRouter<SinkRecord> router = newRouterWithConfig(cfg);

        SinkRecord out = router.apply(newRecord(baseHeaders()));

        assertEquals("test.simple_sensor", out.topic());
    }

    @Test
    void shouldUseConfiguredServiceAsLiteralWhenNoSuchHeaderExists() {
        Map<String, String> cfg = new HashMap<>();
        cfg.put("datamodel", "dm-postgis-errors");
        cfg.put("headers.service", "fixed");
        HeaderRouter<SinkRecord> router = newRouterWithConfig(cfg);

        SinkRecord out = router.apply(newRecord(baseHeaders()));

        assertEquals("fixed.fixed_error_log", out.topic());
    }

    @Test
    void shouldReadConfiguredHeaderNamesWhenHeadersExist() {
        Map<String, String> cfg = new HashMap<>();
        cfg.put("headers.service", "x-service");
        cfg.put("headers.servicepath", "x-servicepath");
        cfg.put("headers.entitytype", "x-type");
        cfg.put("headers.suffix", "x-suffix");
        cfg.put("headers.datamodel", "x-datamodel");
        HeaderRouter<SinkRecord> router = newRouterWithConfig(cfg);

        Map<String, String> headers = new HashMap<>();
        headers.put("x-service", "svc");
        headers.put("x-servicepath", "path");
        headers.put("x-type", "room");
        headers.put("x-suffix", "_lastdata");
        headers.put("x-datamodel", "dm-by-entity-type-database-schema");

        SinkRecord out = router.apply(newRecord(headers));

        assertEquals("path.path_room_lastdata", out.topic());
    }

    // === Record handling ===

    @Test
    void shouldPreserveRecordContentsWhenRouting() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database");
        SinkRecord in = newRecord(baseHeaders());

        SinkRecord out = router.apply(in);

        assertEquals(in.kafkaPartition(), out.kafkaPartition());
        assertEquals(in.key(), out.key());
        assertEquals(in.value(), out.value());
        assertEquals(in.timestamp(), out.timestamp());
        assertSame(in.headers(), out.headers());
    }

    @Test
    void shouldExposeConfigDef() {
        HeaderRouter<SinkRecord> router = newRouter("dm-by-entity-type-database");

        assertTrue(router.config().names().contains("datamodel"));
        router.close();
    }

    private HeaderRouter<SinkRecord> newRouter(String configuredDatamodel) {
        Map<String, String> cfg = new HashMap<>();
        if (configuredDatamodel != null) {
            cfg.put("datamodel", configuredDatamodel);
        }
        return newRouterWithConfig(cfg);
    }

    private HeaderRouter<SinkRecord> newRouterWithConfig(Map<String, String> cfg) {
        HeaderRouter<SinkRecord> router = new HeaderRouter<>();
        router.configure(cfg);
        return router;
    }

    private SinkRecord newRecord(Map<String, String> headers) {
        SinkRecord record = new SinkRecord(
                "input-topic",
                0,
                null,
                null,
                null,
                Map.of("dummy", "value"),
                0L
        );

        // A null value adds the header without value, to exercise null handling
        headers.forEach((k, v) -> {
            if (v != null) {
                record.headers().addString(k, v);
            } else {
                record.headers().add(k, null, null);
            }
        });

        return record;
    }

    private Map<String, String> baseHeaders() {
        Map<String, String> h = new HashMap<>();
        h.put("fiware-service", "test");
        h.put("fiware-servicepath", "simple");
        h.put("entityType", "sensor");
        h.put("entityId", "sensor1");
        h.put("suffix", "");
        return h;
    }
}