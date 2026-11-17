// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (C) 2026 Taeho Lee
//
// This source describes Open Hardware and is licensed under the CERN-OHL-P v2.
// You may redistribute and modify this documentation and make products using
// it under the terms of the CERN-OHL-P v2 (https://cern.ch/cern-ohl). This
// documentation is distributed WITHOUT ANY EXPRESS OR IMPLIED WARRANTY,
// INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS FOR A
// PARTICULAR PURPOSE. Please see the CERN-OHL-P v2 for applicable conditions.
//
// The unit table: the numbers an emitted inquiry names.
//
// A selector in a table emitted for a substrate means the unit this file gives it, and nothing else. The generator
// under boards/ reads these numbers from here, so an emitter and a substrate cannot disagree about which unit a
// selector means, and a new unit is one line in one place rather than a convention in a board's README.
//
// A selector a substrate does not carry answers zero, so an inquiry that names a missing unit fails rather than
// passing.

`ifndef SSCCS_UNITS_SVH
`define SSCCS_UNITS_SVH

`define UNIT_EVEN       3'd0
`define UNIT_RANGE_010  3'd1

`define COMPOSE_AND     1'b0
`define COMPOSE_OR      1'b1

`endif
