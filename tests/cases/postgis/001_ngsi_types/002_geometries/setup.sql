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
*
* Authors:
*  - Álvaro Vega
*  - Gregorio Blázquez
*  - Fermín Galán
*  - Oriana Romero
*/

-- Drop table
DROP TABLE IF EXISTS test.parking_zone;

-- Create table
CREATE TABLE test.parking_zone (
	timeinstant timestamptz NOT NULL,
	"location" public.geometry(point) NULL,
	polygon public.geometry(polygon) NULL,
	linestring public.geometry(linestring) NULL,
	multipoint public.geometry(multipoint) NULL,
	multilinestring public.geometry(multilinestring) NULL,
	multipolygon public.geometry(multipolygon) NULL,
	zoneignored public.geometry(polygon) NULL,
	feature public.geometry(point) NULL,
	featurecollection public.geometry(polygon) NULL,
	"name" text NULL,
	zip text NULL,
	"zone" text NULL,
	entityid text NOT NULL,
	entitytype text NULL,
	recvtime timestamptz NOT NULL,
	fiwareservicepath text NULL
);
CREATE INDEX parking_zone_idx_gidx ON test.parking_zone USING gist (location);
CREATE INDEX parking_zone_idx_linestring ON test.parking_zone USING gist (linestring);
CREATE INDEX parking_zone_idx_multipoint ON test.parking_zone USING gist (multipoint);
CREATE INDEX parking_zone_idx_multilinestring ON test.parking_zone USING gist (multilinestring);
CREATE INDEX parking_zone_idx_multipolygon ON test.parking_zone USING gist (multipolygon);
CREATE INDEX parking_zone_idx_zip ON test.parking_zone USING btree (zip, timeinstant);
CREATE INDEX parking_zone_idx_zon ON test.parking_zone USING btree (zone, timeinstant);
CREATE INDEX parking_zone_timeinstant_idx ON test.parking_zone USING btree (timeinstant DESC);