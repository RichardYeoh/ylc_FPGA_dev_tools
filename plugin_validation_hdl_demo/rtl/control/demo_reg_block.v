module demo_reg_block (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_wr_en,
    input  wire [3:0]   cfg_addr,
    input  wire [31:0]  cfg_wr_data,
    output reg          core_enable,
    output reg  [15:0]  tick_divider,
    output reg  [11:0]  pwm_period,
    output reg  [11:0]  pwm_high_cycles,
    output reg  [7:0]   blink_divider
);

    localparam logic [3:0] AddrCtrl      = 4'h0;
    localparam logic [3:0] AddrTickDiv   = 4'h1;
    localparam logic [3:0] AddrPwmPeriod = 4'h2;
    localparam logic [3:0] AddrPwmHigh   = 4'h3;
    localparam logic [3:0] AddrBlinkDiv  = 4'h4;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            core_enable <= 1'b0;
            tick_divider <= 16'd4;
            pwm_period <= 12'd8;
            pwm_high_cycles <= 12'd4;
            blink_divider <= 8'd8;
        end else if (cfg_wr_en) begin
            case (cfg_addr)
                AddrCtrl: begin
                    core_enable <= cfg_wr_data[0];
                end
                AddrTickDiv: begin
                    tick_divider <= cfg_wr_data[15:0];
                end
                AddrPwmPeriod: begin
                    pwm_period <= cfg_wr_data[11:0];
                end
                AddrPwmHigh: begin
                    pwm_high_cycles <= cfg_wr_data[11:0];
                end
                AddrBlinkDiv: begin
                    blink_divider <= cfg_wr_data[7:0];
                end
                default: begin
                    core_enable <= core_enable;
                    tick_divider <= tick_divider;
                    pwm_period <= pwm_period;
                    pwm_high_cycles <= pwm_high_cycles;
                    blink_divider <= blink_divider;
                end
            endcase
        end
    end

endmodule
