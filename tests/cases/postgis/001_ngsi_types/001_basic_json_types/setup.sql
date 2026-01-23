/**
* Copyright 2026 Telefónica Soluciones de Informática y Comunicaciones de España, S.A.U.
*
* This file includes or is based on software originally developed by Confluent Inc.
* and has been modified by Telefónica Soluciones de Informática y Comunicaciones
* de España, S.A.U.
*
* Licensed under the Confluent Community License, Version 1.0.
* You may obtain a copy of the License at:
*
*   http://www.confluent.io/confluent-community-license
*
* This software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
* CONDITIONS OF ANY KIND, either express or implied.
*/

-- Drop table
DROP TABLE IF EXISTS test.types_zone;

-- Create table
CREATE TABLE IF NOT EXISTS test.types_zone (
    recvtime TIMESTAMPTZ NOT NULL DEFAULT now(),
    fiwareservicepath TEXT,
    entityid TEXT,
    entitytype TEXT,
    timeinstant TIMESTAMPTZ,

    -- Basic JSON types mapped to PG types
    str_col TEXT,
    number_col DOUBLE PRECISION,
    bool_col BOOLEAN,
    null_col TEXT,
    obj_col JSONB,
    array_col JSONB,

    CONSTRAINT types_zone_pkey PRIMARY KEY (timeinstant, entityid)
);