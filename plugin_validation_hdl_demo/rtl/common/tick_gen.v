module tick_gen #(
    parameter integer COUNTER_WIDTH = 16
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,
    input  wire [COUNTER_WIDTH-1:0]     cfg_divider,
    output reg                          tick
);

    reg [COUNTER_WIDTH-1:0] counter_reg;
    wire [COUNTER_WIDTH-1:0] divider_safe;
    wire hit_terminal;

    assign divider_safe = (cfg_divider == {COUNTER_WIDTH{1'b0}})
        ? {{(COUNTER_WIDTH-1){1'b0}}, 1'b1}
        : cfg_divider;
    assign hit_terminal = (counter_reg == divider_safe - {{(COUNTER_WIDTH-1){1'b0}}, 1'b1});

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter_reg <= {COUNTER_WIDTH{1'b0}};
            tick <= 1'b0;
        end else if (!enable) begin
            counter_reg <= {COUNTER_WIDTH{1'b0}};
            tick <= 1'b0;
        end else if (hit_terminal) begin
            counter_reg <= {COUNTER_WIDTH{1'b0}};
            tick <= 1'b1;
        end else begin
            counter_reg <= counter_reg + {{(COUNTER_WIDTH-1){1'b0}}, 1'b1};
            tick <= 1'b0;
        end
    end

endmodule
