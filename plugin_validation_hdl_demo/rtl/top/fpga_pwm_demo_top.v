module fpga_pwm_demo_top (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        cfg_wr_en,
    input  wire [3:0]  cfg_addr,
    input  wire [31:0] cfg_wr_data,
    output wire        pwm_out,
    output reg         heartbeat_led,
    output wire [11:0] debug_phase
);

    wire        core_enable;
    wire [15:0] tick_divider;
    wire [11:0] pwm_period;
    wire [11:0] pwm_high_cycles;
    wire [7:0]  blink_divider;
    wire        slow_tick;

    reg [7:0] heartbeat_cnt;

    demo_reg_block u_demo_reg_block (
        .clk(clk),
        .rst_n(rst_n),
        .cfg_wr_en(cfg_wr_en),
        .cfg_addr(cfg_addr),
        .cfg_wr_data(cfg_wr_data),
        .core_enable(core_enable),
        .tick_divider(tick_divider),
        .pwm_period(pwm_period),
        .pwm_high_cycles(pwm_high_cycles),
        .blink_divider(blink_divider)
    );

    tick_gen #(
        .COUNTER_WIDTH(16)
    ) u_tick_gen (
        .clk(clk),
        .rst_n(rst_n),
        .enable(core_enable),
        .cfg_divider(tick_divider),
        .tick(slow_tick)
    );

    pwm_core #(
        .COUNTER_WIDTH(12)
    ) u_pwm_core (
        .clk(clk),
        .rst_n(rst_n),
        .step_tick(slow_tick),
        .enable(core_enable),
        .cfg_period(pwm_period),
        .cfg_high_cycles(pwm_high_cycles),
        .pwm_out(pwm_out),
        .phase_count(debug_phase)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            heartbeat_cnt <= 8'd0;
            heartbeat_led <= 1'b0;
        end else if (!core_enable) begin
            heartbeat_cnt <= 8'd0;
            heartbeat_led <= 1'b0;
        end else if (slow_tick) begin
            if (heartbeat_cnt == blink_divider - 8'd1) begin
                heartbeat_cnt <= 8'd0;
                heartbeat_led <= ~heartbeat_led;
            end else begin
                heartbeat_cnt <= heartbeat_cnt + 8'd1;
            end
        end
    end

endmodule
