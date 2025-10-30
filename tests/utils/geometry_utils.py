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

import base64
from shapely import wkt
from shapely.geometry.base import BaseGeometry
from shapely.geometry import shape
from config import logger

def to_wkb_struct_from_wkt(wkt_str: str, field_name: str, srid: int = 4326):
    """
    Converts a WKT geometry string to a Debezium-compatible WKB struct
    with schema and base64-encoded payload.
    """
    try:
        geom: BaseGeometry = wkt.loads(wkt_str)
        wkb_bytes = geom.wkb
        wkb_b64 = base64.b64encode(wkb_bytes).decode("ascii")

        return {
            "schema": {
                "field": field_name,
                "type": "struct",
                "name": "io.confluent.connect.jdbc.data.geometry.Geometry",
                "fields": [
                    {"field": "wkb", "type": "bytes"},
                    {"field": "srid", "type": "int32"}
                ],
                "optional": False
            },
            "payload": {
                "wkb": wkb_b64,
                "srid": srid
            }
        }
    except Exception as e:
        print(f"[WARN] Error generating WKB from WKT '{wkt_str}': {e}")
        return None

def to_wkb_struct_from_geojson(geojson_attr, field_name, srid=4326):
    """
    Converts a GeoJSON-style geometry attribute to a Kafka Connect-compatible WKB struct.
    Expected input:
    {
      "type": "geo:json",
      "value": {
        "type": "Point" | "Polygon" | "LineString" | ...,
        "coordinates": [...]
      }
    }
    Returns a dict with 'schema' and 'payload' keys.
    """
    try:
        if not isinstance(geojson_attr, dict):
            raise ValueError("geojson_attr must be a dict")

        if geojson_attr.get("type") != "geo:json" or "value" not in geojson_attr:
            raise ValueError("Invalid geojson_attr format")

        geom = shape(geojson_attr["value"])
        wkb_bytes = geom.wkb
        wkb_b64 = base64.b64encode(wkb_bytes).decode("ascii")

        schema = {
            "type": "struct",
            "name": "io.confluent.connect.jdbc.data.geometry.Geometry",
            "fields": [
                {"field": "wkb", "type": "bytes", "optional": False},
                {"field": "srid", "type": "int32", "optional": False},
            ],
            "optional": False,
        }

        payload = {"wkb": wkb_b64, "srid": srid}

        return {"schema": schema, "payload": payload}

    except Exception as e:
        logger.error(f"Error converting GeoJSON to WKB for field '{field_name}': {e}")
        return None