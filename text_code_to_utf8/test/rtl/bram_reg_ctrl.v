`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2025/10/24 13:58:21
// Design Name: 
// Module Name: bram_reg_ctrl
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


module bram_reg_ctrl(

	input					sys_clk					,
	input					sys_rst_n				,
	
	input 		[15:0]		BRAM_PORTA_0_addr		,
	input		[31:0]		BRAM_PORTA_0_din    	,
	output	reg	[31:0]		BRAM_PORTA_0_dout   	,
	input 					BRAM_PORTA_0_en     	,
	input 		[3:0]		BRAM_PORTA_0_we     	,

	input		[5:0]		mm2s_frame_ptr_out_r	,
	input		[5:0]		s2mm_frame_ptr_out_w	

    );

//ps 读	
always@(posedge sys_clk or negedge sys_rst_n)
begin
	if(!sys_rst_n)
		BRAM_PORTA_0_dout <= 'd0;
	else
		case(BRAM_PORTA_0_addr)
			'h0000	:	BRAM_PORTA_0_dout <= 'h2025_1024 ;	//2025年10月25日
			'h0004	:	BRAM_PORTA_0_dout <= 'h1400_1000 ;	//14点00分	V1.0.00
			'h0008	:	BRAM_PORTA_0_dout <= mm2s_frame_ptr_out_r ;	//14点00分	V1.0.00
			'h000C	:	BRAM_PORTA_0_dout <= s2mm_frame_ptr_out_w ;	//14点00分	V1.0.00

			default:		BRAM_PORTA_0_dout <= 'd0;
		endcase
end	
	
	
	
	
	
endmodule
