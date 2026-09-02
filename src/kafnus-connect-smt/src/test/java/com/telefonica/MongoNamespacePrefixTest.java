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

class MongoNamespacePrefixTest {

    @Test
    void shouldFailWhenPrefixConfigIsMissing() {
        MongoNamespacePrefix<SinkRecord> smt = new MongoNamespacePrefix<>();

        assertThrows(ConfigException.class, () -> smt.configure(Map.of()));
    }

    @Test
    void shouldFailWhenPrefixConfigIsEmpty() {
        MongoNamespacePrefix<SinkRecord> smt = new MongoNamespacePrefix<>();

        assertThrows(ConfigException.class, () -> smt.configure(Map.of("prefix", "")));
    }

    @Test
    void shouldUseSplitPrefixesWhenConfigured() {
        MongoNamespacePrefix<SinkRecord> smt = new MongoNamespacePrefix<>();
        smt.configure(Map.of(
            "dbname.prefix", "db_",
            "collection.prefix", "col_"
        ));

        Map<String, Object> key = new HashMap<>();
        key.put("database", "test");
        key.put("collection", "simple");

        SinkRecord out = smt.apply(newRecord(key));

        @SuppressWarnings("unchecked")
        Map<String, Object> outKey = (Map<String, Object>) out.key();
        assertEquals("db_test", outKey.get("database"));
        assertEquals("col_simple", outKey.get("collection"));
    }

    @Test
    void shouldUseLegacySharedPrefixAsFallback() {
        MongoNamespacePrefix<SinkRecord> smt = new MongoNamespacePrefix<>();
        smt.configure(Map.of("prefix", "sth_"));

        Map<String, Object> key = new HashMap<>();
        key.put("database", "test");
        key.put("collection", "simple");

        SinkRecord out = smt.apply(newRecord(key));

        @SuppressWarnings("unchecked")
        Map<String, Object> outKey = (Map<String, Object>) out.key();
        assertEquals("sth_test", outKey.get("database"));
        assertEquals("sth_simple", outKey.get("collection"));
    }

    @Test
    void shouldReturnSameRecordWhenKeyIsNull() {
        MongoNamespacePrefix<SinkRecord> smt = newSmt("sth_");
        SinkRecord record = new SinkRecord("topic", 0, null, null, null, Map.of("v", 1), 0L);

        SinkRecord out = smt.apply(record);

        assertSame(record, out);
    }

    @Test
    void shouldFailWhenKeyIsNotMap() {
        MongoNamespacePrefix<SinkRecord> smt = newSmt("sth_");
        SinkRecord record = new SinkRecord("topic", 0, null, "not-a-map", null, Map.of("v", 1), 0L);

        assertThrows(ConfigException.class, () -> smt.apply(record));
    }

    @Test
    void shouldReturnSameRecordWhenRequiredFieldsAreMissing() {
        MongoNamespacePrefix<SinkRecord> smt = newSmt("sth_");
        Map<String, Object> key = new HashMap<>();
        key.put("database", "test");

        SinkRecord record = newRecord(key);
        SinkRecord out = smt.apply(record);

        assertSame(record, out);
    }

    @Test
    void shouldPrefixBothDatabaseAndCollectionWhenNeeded() {
        MongoNamespacePrefix<SinkRecord> smt = newSmt("sth_");
        Map<String, Object> originalKey = new HashMap<>();
        originalKey.put("database", "test");
        originalKey.put("collection", "simple");

        SinkRecord out = smt.apply(newRecord(originalKey));

        @SuppressWarnings("unchecked")
        Map<String, Object> outKey = (Map<String, Object>) out.key();
        assertEquals("sth_test", outKey.get("database"));
        assertEquals("sth_simple", outKey.get("collection"));
        assertEquals("test", originalKey.get("database"));
        assertEquals("simple", originalKey.get("collection"));
    }

    @Test
    void shouldNotModifyRecordWhenBothFieldsAlreadyPrefixed() {
        MongoNamespacePrefix<SinkRecord> smt = newSmt("sth_");
        Map<String, Object> key = new HashMap<>();
        key.put("database", "sth_test");
        key.put("collection", "sth_simple");

        SinkRecord record = newRecord(key);
        SinkRecord out = smt.apply(record);

        assertSame(record, out);
    }

    @Test
    void shouldPrefixOnlyMissingFieldWhenPartiallyPrefixed() {
        MongoNamespacePrefix<SinkRecord> smt = newSmt("sth_");
        Map<String, Object> key = new HashMap<>();
        key.put("database", "sth_test");
        key.put("collection", "simple");

        SinkRecord out = smt.apply(newRecord(key));

        @SuppressWarnings("unchecked")
        Map<String, Object> outKey = (Map<String, Object>) out.key();
        assertEquals("sth_test", outKey.get("database"));
        assertEquals("sth_simple", outKey.get("collection"));
    }

    @Test
    void configShouldExposePrefixParameter() {
        MongoNamespacePrefix<SinkRecord> smt = new MongoNamespacePrefix<>();

        assertTrue(smt.config().names().contains("prefix"));
        assertTrue(smt.config().names().contains("dbname.prefix"));
        assertTrue(smt.config().names().contains("collection.prefix"));
    }

    private MongoNamespacePrefix<SinkRecord> newSmt(String prefix) {
        MongoNamespacePrefix<SinkRecord> smt = new MongoNamespacePrefix<>();
        smt.configure(Map.of("prefix", prefix));
        return smt;
    }

    private SinkRecord newRecord(Map<String, Object> key) {
        return new SinkRecord("input-topic", 0, null, key, null, Map.of("dummy", "value"), 0L);
    }
}