module pwm_core #(
    parameter integer COUNTER_WIDTH = 12
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         step_tick,
    input  wire                         enable,
    input  wire [COUNTER_WIDTH-1:0]     cfg_period,
    input  wire [COUNTER_WIDTH-1:0]     cfg_high_cycles,
    output reg                          pwm_out,
    output reg  [COUNTER_WIDTH-1:0]     phase_count
);

    wire [COUNTER_WIDTH-1:0] period_safe;
    wire [COUNTER_WIDTH-1:0] high_safe;
    wire wrap_now;

    assign period_safe = (cfg_period < {{(COUNTER_WIDTH-1){1'b0}}, 1'b1})
        ? {{(COUNTER_WIDTH-1){1'b0}}, 1'b1}
        : cfg_period;
    assign high_safe = (cfg_high_cycles > period_safe) ? period_safe : cfg_high_cycles;
    assign wrap_now = (phase_count == period_safe - {{(COUNTER_WIDTH-1){1'b0}}, 1'b1});

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase_count <= {COUNTER_WIDTH{1'b0}};
            pwm_out <= 1'b0;
        end else if (!enable) begin
            phase_count <= {COUNTER_WIDTH{1'b0}};
            pwm_out <= 1'b0;
        end else if (step_tick) begin
            if (wrap_now) begin
                phase_count <= {COUNTER_WIDTH{1'b0}};
                pwm_out <= (high_safe != {COUNTER_WIDTH{1'b0}});
            end else begin
                phase_count <= phase_count + {{(COUNTER_WIDTH-1){1'b0}}, 1'b1};
                pwm_out <= ((phase_count + {{(COUNTER_WIDTH-1){1'b0}}, 1'b1}) < high_safe);
            end
        end
    end

endmodule
