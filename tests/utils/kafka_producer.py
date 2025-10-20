# Copyright 2025 Telefónica Soluciones de Informática y Comunicaciones de España, S.A.U.
# PROJECT: Kafnus
#
# This software and / or computer program has been developed by Telefónica Soluciones
# de Informática y Comunicaciones de España, S.A.U (hereinafter TSOL) and is protected
# as copyright by the applicable legislation on intellectual property.
#
# It belongs to TSOL, and / or its licensors, the exclusive rights of reproduction,
# distribution, public communication and transformation, and any economic right on it,
# all without prejudice of the moral rights of the authors mentioned above. It is expressly
# forbidden to decompile, disassemble, reverse engineer, sublicense or otherwise transmit
# by any means, translate or create derivative works of the software and / or computer
# programs, and perform with respect to all or part of such programs, any type of exploitation.
#
# Any use of all or part of the software and / or computer program will require the
# express written consent of TSOL. In all cases, it will be necessary to make
# an express reference to TSOL ownership in the software and / or computer
# program.
#
# Non-fulfillment of the provisions set forth herein and, in general, any violation of
# the peaceful possession and ownership of these rights will be prosecuted by the means
# provided in both Spanish and international law. TSOL reserves any civil or
# criminal actions it may exercise to protect its rights.

from kafka import KafkaProducer
from datetime import datetime
import json
from pathlib import Path
from config import logger
from utils.geometry_utils import to_wkb_struct_from_wkt, to_wkb_struct_from_geojson

def infer_type(value):
    """
    Infer a Kafka Connect compatible schema type string from a Python value.

    Returns one of: "boolean", "int32", "double", "struct", or "string".

    Inputs:
    - value: any Python object to inspect

    Output:
    - type string usable in a Kafka Connect schema field definition
    """
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "int32"
    if isinstance(value, float):
        return "double"
    return "string"

def normalize_field(key, value):
    """
    Normalizes a field to extract value and type.
    If type is provided explicitly, uses it; otherwise infers it.
    """
    # Detect GeoJSON geometry
    if isinstance(value, dict) and value.get("type") == "geo:json":
        geom_struct = to_wkb_struct_from_geojson(value, key)
        if geom_struct:
            geom_schema = geom_struct["schema"]
            geom_payload = geom_struct["payload"]
            return key, geom_payload, geom_schema, False
    
    # Detect geometry dicts
    if isinstance(value, dict) and "wkb" in value and "srid" in value:
        geom_schema = {
            "type": "struct",
            "name": "io.confluent.connect.jdbc.data.geometry.Geometry",
            "fields": [
                {"field": "wkb", "type": "bytes", "optional": False},
                {"field": "srid", "type": "int32", "optional": False},
            ],
            "optional": False,
        }
        geom_payload = {"wkb": value["wkb"], "srid": value["srid"]}
        return key, geom_payload, geom_schema, False


    # Detect geometry WKT strings
    if isinstance(value, str) and any(value.strip().upper().startswith(prefix) 
                                 for prefix in ["POINT", "POLYGON", "LINESTRING", "MULTIPOINT"]):
        geom_struct = to_wkb_struct_from_wkt(value, key)
        if geom_struct:
            geom_schema = geom_struct["schema"]
            geom_payload = geom_struct["payload"]
            return key, geom_payload, geom_schema, False

    # Si viene con metadatos explícitos:
    if isinstance(value, dict) and "value" in value:
        val = value["value"]
        type_ = value.get("type", infer_type(val))
        optional = value.get("optional", val is None)
    else:
        val = value
        type_ = infer_type(val)
        optional = val is None

    # Serializa listas o diccionarios a string JSON
    if isinstance(val, (dict, list)):
        val = json.dumps(val, ensure_ascii=False)

    return key, val, type_, optional

def build_key_schema(payload, key_fields):
    """
    Builds a Kafka Connect-style key with schema + payload.

    The function inspects `payload` for the given `key_fields` and constructs
    a dictionary with the Connect `schema` (type struct and fields metadata)
    and the corresponding `payload` containing only the key fields.

    Inputs:
    - payload: dict containing the record fields
    - key_fields: iterable of field names that should be included in the key

    Returns:
    - dict with keys `schema` and `payload` suitable to be used as a message key,
      or None if none of the requested key_fields are present in payload.
    """
    schema_fields = []
    key_payload = {}
    for field in key_fields:
        if field in payload:
            _, val, type_, _ = normalize_field(field, payload[field])
            schema_fields.append({"field": field, "type": type_, "optional": False})
            key_payload[field] = val
    if not key_payload:
        return None
    return {"schema": {"type": "struct", "fields": schema_fields, "optional": False}, "payload": key_payload}

def build_message(item):
    """
    Build a message object from an input descriptor.

    The input `item` should be a dict describing a message to produce. Supported
    message `type`s are `postgis` and `mongo`. The function will add a
    `recvtime` to the record if missing, build a Kafka Connect-style value and
    optionally a key and headers depending on the message type.

    Returns a dict with keys: `topic`, `value`, `headers`, and `key`.
    """
    msg_type = item.get("type")
    topic = item.get("topic")
    record = dict(item.get("record", {}))

    # Always add recvtime if it does not exist
    if "recvtime" not in record:
        record["recvtime"] = datetime.utcnow().isoformat() + "Z"

    if msg_type == "postgis":
        target_table = item.get("target_table")
        if not target_table:
            raise ValueError("Missing 'target_table' for postgis message")

        # Build schema and payload for PostGIS messages
        fields = []
        payload = {}
        for k, v in record.items():
            _, val, type_, optional = normalize_field(k, v)
            if isinstance(type_, dict) and type_.get("type") == "struct":
                field_def = {"field": k, **type_}
            else:
                field_def = {"field": k, "type": type_, "optional": optional}
            fields.append(field_def)
            payload[k] = val

        schema = {"type": "struct", "fields": fields, "optional": False}
        value = {"schema": schema, "payload": payload}
        headers = [("target_table", target_table.encode("utf-8"))]
        key = build_key_schema(payload, ["entityid"])

    elif msg_type == "mongo":
        # Mongo uses database and collection outside the record
        db = item.get("database", "sth_test")
        collection = item.get("collection", "default_collection")
        key = {"database": db, "collection": collection}

        # The value only carries the record data + recvtime
        value = dict(record)
        headers = []  # NO_HEADERS

    elif msg_type == "http":
        # Por ahora skip
        return None

    else:
        raise ValueError(f"Unknown type {msg_type}")

    return {"topic": topic, "value": value, "headers": headers, "key": key}

def load_input(json_path: Path):
    """
    Load one or more message descriptors from a JSON file.

    The file can contain a single JSON object or an array of objects. Each
    object is passed to `build_message` and only valid messages are returned.

    Input:
    - json_path: Path to the JSON file

    Output:
    - list of message dicts suitable for `produce_messages`
    """
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        data = [data]

    messages = []
    for item in data:
        msg = build_message(item)
        if msg:
            messages.append(msg)
    return messages


def produce_messages(kafka_bootstrap, messages):
    """
    Produce a list of messages to Kafka using kafka-python's KafkaProducer.

    Inputs:
    - kafka_bootstrap: bootstrap server string or list
    - messages: list of dicts as returned by `build_message` / `load_input`

    The function serializes both key and value as JSON and logs each send.
    """
    producer = KafkaProducer(
        bootstrap_servers=kafka_bootstrap,
        key_serializer=lambda k: json.dumps(k).encode("utf-8") if k else None,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    for msg in messages:
        producer.send(
            msg["topic"],
            key=msg.get("key"),
            value=msg["value"],
            headers=msg.get("headers", [])
        )
        logger.info(f"📤 Sent to {msg['topic']} key={json.dumps(msg.get('key'), ensure_ascii=False)} value={json.dumps(msg['value'], ensure_ascii=False)}")
    producer.flush()
