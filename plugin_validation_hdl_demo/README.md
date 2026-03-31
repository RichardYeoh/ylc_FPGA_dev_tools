# Plugin Validation HDL Demo

## Purpose

This temporary project is used to validate the current VS Code FPGA/HDL setup.

It contains:

- Multi-level Verilog RTL
- A runnable SystemVerilog testbench
- A sample XDC constraint file
- A sample Vivado Tcl script

## Structure

- `rtl/common` : Reusable low-level building blocks
- `rtl/control` : Register/configuration block
- `rtl/pwm` : PWM datapath
- `rtl/top` : Top-level integration
- `tb` : Simulation testbench
- `constraints` : Sample Vivado constraints
- `scripts` : Sample Vivado Tcl flow

## Expected Validation Coverage

- VS Code HDL language recognition
- Verible formatting
- Verible lint
- Verilator lint
- Icarus Verilog compilation
- VVP simulation execution
- Ctags tag generation
