// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Research in progress. Read, check, and cite it. See LICENSE at the root of
// this proof of concept before copying it into another work.
//
// The unit table: the numbers an emitted inquiry names.
//
// A selector names a kind of constraint. The bound it applies is data, so one unit serves every bound and a
// table can state a constraint this file has never heard of. A selector in a table emitted for a substrate means
// the unit this file gives it.
//
// A coordinate is a signed 64-bit value and every order comparison is signed. The reference assembly compares with
// slt and the Rust fallback compares i64, so an unsigned compare in a substrate would put every negative
// coordinate above every positive one and the anchors would catch it., and nothing else. The generator
// under boards/ reads these numbers from here, so an emitter and a substrate cannot disagree about which unit a
// selector means, and a new unit is one line in one place rather than a convention in a board's README.
//
// A selector a substrate does not carry answers zero, so an inquiry that names a missing unit fails rather than
// passing.

`ifndef SSCCS_UNITS_SVH
`define SSCCS_UNITS_SVH

`define UNIT_EVEN       3'd0
`define UNIT_RANGE      3'd1
`define UNIT_EQ         3'd2
`define UNIT_GT         3'd3

`define COMPOSE_AND     1'b0
`define COMPOSE_OR      1'b1

`endif
