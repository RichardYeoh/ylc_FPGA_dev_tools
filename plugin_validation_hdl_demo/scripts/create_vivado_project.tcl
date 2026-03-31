# Create a temporary Vivado project for editor validation / 创建用于编辑器验证的临时 Vivado 工程

set project_name "plugin_validation_hdl_demo"
set project_dir  [file normalize "./vivado_demo_project"]
set origin_dir   [file normalize ".."]

create_project $project_name $project_dir -force
set_property target_language Verilog [current_project]

add_files [list \
    [file join $origin_dir rtl common tick_gen.v] \
    [file join $origin_dir rtl pwm pwm_core.v] \
    [file join $origin_dir rtl control demo_reg_block.v] \
    [file join $origin_dir rtl top fpga_pwm_demo_top.v] \
]

add_files -fileset constrs_1 [list \
    [file join $origin_dir constraints fpga_pwm_demo.xdc] \
]

update_compile_order -fileset sources_1
update_compile_order -fileset sim_1
