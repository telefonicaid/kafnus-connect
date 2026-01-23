# Copyright 2026 Telefónica Soluciones de Informática y Comunicaciones de España, S.A.U.
#
# This file includes or is based on software originally developed by Confluent Inc.
# and has been modified by Telefónica Soluciones de Informática y Comunicaciones
# de España, S.A.U.
#
# Licensed under the Confluent Community License, Version 1.0.
# You may obtain a copy of the License at:
#
#   http://www.confluent.io/confluent-community-license
#
# This software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied.
#
# Authors:
#  - Álvaro Vega
#  - Gregorio Blázquez
#  - Fermín Galán
#  - Oriana Romero

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