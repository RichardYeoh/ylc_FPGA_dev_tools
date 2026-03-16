`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2025/10/14 13:50:51
// Design Name: 
// Module Name: bram_info_wr
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module bram_info_wr(
    input                   ui_clk
    ,input                  ui_rst
    ,input [5:0]            s2mm_frame_ptr_out_w
    ,output                 BRAM_PORTB_clk
    ,output                 BRAM_PORTB_rst
    ,output                 BRAM_PORTB_en
    ,output [3:0]           BRAM_PORTB_we
    ,output [31:0]          BRAM_PORTB_addr
    ,output [31:0]          BRAM_PORTB_din
    ,input [31:0]           BRAM_PORTB_dout
     
    );
reg    [31:0]                  info_reg;
always@(posedge ui_clk or posedge ui_rst) begin
   if (ui_rst) begin
      info_reg <= 32'h0;
   end else begin
      info_reg <= {26'h0,s2mm_frame_ptr_out_w};
   end
end

assign BRAM_PORTB_clk   = ui_clk;
assign BRAM_PORTB_rst   = ui_rst;
assign BRAM_PORTB_en    = 1'b1;
assign BRAM_PORTB_we    = 4'hF;
assign BRAM_PORTB_addr  = 32'h00000000;
assign BRAM_PORTB_din   = info_reg;
endmodule
