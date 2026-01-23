/*
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

-- setup_tests.sql
CREATE EXTENSION IF NOT EXISTS postgis;

-- Drop schema
DROP SCHEMA IF EXISTS test CASCADE;
-- Create schema
CREATE SCHEMA test;

-- Create table for error logging
CREATE TABLE test.test_error_log (
    "timestamp" TIMESTAMPTZ NOT NULL,
    error TEXT NOT NULL,
    query TEXT NULL
);