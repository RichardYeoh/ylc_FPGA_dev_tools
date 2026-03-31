## Example clock constraint / 示例时钟约束
create_clock -name sys_clk -period 10.000 [get_ports clk]

## Example I/O standards / 示例 I/O 标准
set_property IOSTANDARD LVCMOS33 [get_ports clk]
set_property IOSTANDARD LVCMOS33 [get_ports rst_n]
set_property IOSTANDARD LVCMOS33 [get_ports pwm_out]
set_property IOSTANDARD LVCMOS33 [get_ports heartbeat_led]

## Example pin assignment placeholders / 示例引脚分配占位
## set_property PACKAGE_PIN W5  [get_ports clk]
## set_property PACKAGE_PIN V17 [get_ports rst_n]
## set_property PACKAGE_PIN U16 [get_ports pwm_out]
## set_property PACKAGE_PIN E19 [get_ports heartbeat_led]
