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
DROP TABLE IF EXISTS test.order_sensor_lastdata;

-- Create table
CREATE TABLE IF NOT EXISTS test.order_sensor_lastdata (
    recvtime TIMESTAMPTZ NOT NULL,
    fiwareservicepath TEXT,
    entityid TEXT,
    entitytype TEXT,
    timeinstant TIMESTAMPTZ,
    temperature DOUBLE PRECISION,
    CONSTRAINT order_sensor_lastdata_pkey PRIMARY KEY (entityid)
);
