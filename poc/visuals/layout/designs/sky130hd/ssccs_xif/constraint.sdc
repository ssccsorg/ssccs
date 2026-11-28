# SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
# Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
#
# Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
# concept: a copy carries this notice and the revision it was taken from.
#
# XIF coprocessor, SkyWater 130 nm (sky130hd).
# 25 MHz, the carrier board's own crystal.

create_clock -period 40.0 -name clk [get_ports clk]
set_input_delay -clock clk 1.0 [all_inputs -no_clocks]
set_output_delay -clock clk 1.0 [all_outputs]
