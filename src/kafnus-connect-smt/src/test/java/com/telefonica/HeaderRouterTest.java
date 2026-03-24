package com.telefonica;

import org.apache.kafka.common.config.ConfigException;
import org.apache.kafka.connect.sink.SinkRecord;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

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

    private HeaderRouter<SinkRecord> newRouter(String configuredDatamodel) {
        HeaderRouter<SinkRecord> router = new HeaderRouter<>();
        Map<String, String> cfg = new HashMap<>();
        if (configuredDatamodel != null) {
            cfg.put("datamodel", configuredDatamodel);
        }
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

        headers.forEach((k, v) -> {
            if (v != null) {
                record.headers().addString(k, v);
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