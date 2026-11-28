# SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
# Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
#
# Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
# concept: a copy carries this notice and the revision it was taken from.
#
# ORFS design configuration for the XIF coprocessor on sky130hd.
#
# The units are combinational and the coprocessor around them is registered, so
# the standard cell flow has a clock to close against. The period is the
# carrier's 25 MHz crystal, the clock the board designs run on.
#
# The RTL is mounted read-only from baremetal_riscv/sv, so the flow reads the
# units the simulators read rather than a copy that could drift.

export DESIGN_NICKNAME = ssccs_xif
export DESIGN_NAME     = ssccs_xif_coprocessor
export PLATFORM        = sky130hd

export VERILOG_FILES = $(DESIGN_HOME)/src/ssccs_xif/constraints/ck_eq.sv \
                       $(DESIGN_HOME)/src/ssccs_xif/constraints/ck_even.sv \
                       $(DESIGN_HOME)/src/ssccs_xif/constraints/ck_gt.sv \
                       $(DESIGN_HOME)/src/ssccs_xif/constraints/ck_range.sv \
                       $(DESIGN_HOME)/src/ssccs_xif/constraints/ck_range_010.sv \
                       $(DESIGN_HOME)/src/ssccs_xif/projectors/proj_identity.sv \
                       $(DESIGN_HOME)/src/ssccs_xif/projectors/proj_negate.sv \
                       $(DESIGN_HOME)/src/ssccs_xif/projectors/proj_parity.sv \
                       $(DESIGN_HOME)/src/ssccs_xif/projectors/proj_sum2d.sv \
                       $(DESIGN_HOME)/src/ssccs_xif/projectors/proj_sum3d.sv \
                       $(DESIGN_HOME)/src/ssccs_xif/ssccs_xif_coprocessor.sv

export VERILOG_INCLUDE_DIRS = $(DESIGN_HOME)/src/ssccs_xif

export SDC_FILE      = $(DESIGN_HOME)/sky130hd/ssccs_xif/constraint.sdc
export CLOCK_PERIOD  = 40

export CORE_UTILIZATION  = 35
export CORE_ASPECT_RATIO = 1
export CORE_MARGIN       = 2

# kepler-formal crashes with an illegal instruction on the available CPUs. The
# RTL-to-netlist equivalence is proven by the yosys gate in the PoC itself, so
# the in-flow check is redundant here.
export LEC_CHECK = 0
