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

def infer_type(value):
    """Infers the schema type based on Python type."""
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "int32"
    elif isinstance(value, float):
        return "double"
    elif isinstance(value, dict):
        return "struct"
    else:
        return "string"

def normalize_field(key, value):
    """
    Normalizes a field to extract value and type.
    If type is provided explicitly, uses it; otherwise infers it.
    """
    if isinstance(value, dict) and "value" in value:
        val = value["value"]
        type_ = value.get("type", infer_type(val))
    else:
        val = value
        type_ = infer_type(val)
    return key, val, type_

def build_kafnus_message(table_name, record, topic=None):
    """
    Builds a Kafnus Connect message with schema, payload, and target_table header.
    Returns a dict with 'topic', 'value', and 'headers'.
    """
    fields = []
    payload = {}

    for key, value in record.items():
        key, val, type_ = normalize_field(key, value)
        fields.append({
            "field": key,
            "type": type_,
            "optional": False
        })
        payload[key] = val

    # Add recvtime if not present
    if "recvtime" not in payload:
        payload["recvtime"] = datetime.utcnow().isoformat() + "Z"
        fields.append({
            "field": "recvtime",
            "type": "string",
            "optional": False
        })

    schema = {"type": "struct", "fields": fields, "optional": False}

    # Use the topic from input or default to a generic topic
    actual_topic = topic or "kafnus_messages"

    return {
        "topic": actual_topic,
        "value": {"schema": schema, "payload": payload},
        "headers": [("target_table", table_name.encode("utf-8"))]
    }

def build_key_schema(payload, key_fields):
    """
    Builds a Kafka Connect-style key with schema + payload.
    """
    schema_fields = []
    key_payload = {}

    for field in key_fields:
        if field in payload:
            val = payload[field]
            _, val, type_ = normalize_field(field, val)
            schema_fields.append({
                "field": field,
                "type": type_,
                "optional": False
            })
            key_payload[field] = val

    if not key_payload:
        return None

    return {
        "schema": {
            "type": "struct",
            "fields": schema_fields,
            "optional": False
        },
        "payload": key_payload
    }

def load_input(json_path: Path):
    """
    Loads the input JSON file and generates messages ready to send to Kafka with headers.
    """
    logger.debug(f"📂 Loading scenario file: {json_path}")
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    messages = []
    for item in data:
        table = item.get("target_table")
        if not table:
            raise ValueError("Missing 'target_table' field in scenario item.")
        record = item.get("record")
        if not record:
            raise ValueError("Missing 'record' field in scenario item.")
        topic = item.get("topic")  # optional
        msg = build_kafnus_message(table, record, topic=topic)
        messages.append(msg)
    return messages

def produce_messages(kafka_bootstrap, messages, key_fields=["entityid"]):
    """
    Sends the generated messages to Kafka, including headers.
    Uses Connect-style schema for both key and value.
    """
    producer = KafkaProducer(
        bootstrap_servers=kafka_bootstrap,
        key_serializer=lambda k: json.dumps(k).encode("utf-8") if k is not None else None,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    for msg in messages:
        topic = msg["topic"]
        value = msg["value"]
        payload = value.get("payload", {})

        # --- Build structured key ---
        key = build_key_schema(payload, key_fields)
        if not key:
            logger.warning(f"⚠️ No key fields found for {topic}, using null key")

        producer.send(
            topic,
            key=key,
            value=value,
            headers=msg.get("headers", [])
        )

        logger.info(f"📤 Sent to {topic}\n   key={json.dumps(key, ensure_ascii=False)}\n   value={json.dumps(value, ensure_ascii=False)}")

    producer.flush()
