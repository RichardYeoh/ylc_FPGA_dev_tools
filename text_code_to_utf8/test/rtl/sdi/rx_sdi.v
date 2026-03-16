// (c) Copyright 2011 - 2014 Xilinx, Inc. All rights reserved.
//
// This file contains confidential and proprietary information
// of Xilinx, Inc. and is protected under U.S. and
// international copyright and other intellectual property
// laws.
//
//------------------------------------------------------------------------------
//   ____  ____
//  /   /\/   /
// /___/  \  /    Vendor: Xilinx
// \   \   \/     Version: $Revision: #1 $
//  \   \
//  /   /         Filename: $File: //Groups/video_ip/demos/K7/xapp592_k7_sdi_demos_ver2/kc705_sdi_demo/kc705_sdi_demo.v $
// /___/   /\     Timestamp: $DateTime: 2014/03/13 12:31:24 $
// \   \  /  \
//  \___\/\___\
//
// Description:
//      This is the top level module for the Quad SDI demo for Kintex-7 GTX
//      transceivers. It runs on the KC705 board + inrevium TB-FMCH-3GSDI2A FMC
//      mezzanine card.
//------------------------------------------------------------------------------
//
// DISCLAIMER
// This disclaimer is not a license and does not grant any
// rights to the materials distributed herewith. Except as
// otherwise provided in a valid license issued to you by
// Xilinx, and to the maximum extent permitted by applicable
// law: (1) THESE MATERIALS ARE MADE AVAILABLE "AS IS" AND
// WITH ALL FAULTS, AND XILINX HEREBY DISCLAIMS ALL WARRANTIES
// AND CONDITIONS, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING
// BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, NON-
// INFRINGEMENT, OR FITNESS FOR ANY PARTICULAR PURPOSE; and
// (2) Xilinx shall not be liable (whether in contract or tort,
// including negligence, or under any other theory of
// liability) for any loss or damage of any kind or nature
// related to, arising under or in connection with these
// materials, including for any direct, or any indirect,
// special, incidental, or consequential loss or damage
// (including loss of data, profits, goodwill, or any type of
// loss or damage suffered as a result of any action brought
// by a third party) even if such damage or loss was
// reasonably foreseeable or Xilinx had been advised of the
// possibility of the same.
//
// CRITICAL APPLICATIONS
// Xilinx products are not designed or intended to be fail-
// safe, or for use in any application requiring fail-safe
// performance, such as life-support or safety devices or
// systems, Class III medical devices, nuclear facilities,
// applications related to the deployment of airbags, or any
// other applications that could lead to death, personal
// injury, or severe property or environmental damage
// (individually and collectively, "Critical
// Applications"). Customer assumes the sole risk and
// liability of any use of Xilinx products in Critical
// Applications, subject only to applicable laws and
// regulations governing limitations on product liability.
//
// THIS COPYRIGHT NOTICE AND DISCLAIMER MUST BE RETAINED AS
// PART OF THIS FILE AT ALL TIMES.

`timescale 1ns / 1ps
   
module rx_sdi (
    input               rst_n                   ,
	//sar img input
    input               sar_img_clk             ,   
    input             	sar_img_vs              ,
    input             	sar_img_hs              ,
    input             	sar_img_de              ,
    input    [15:0]		sar_img_data            ,	
    
    output             cam_hs                     ,
    output             cam_vs                     ,
    output    [23:0]   cam_rgb		              ,
    output             cam_clk                    ,//74.25m
    output             cam_data_en                

);

wire [7:0] img_red		;   
wire [7:0] img_green    ;
wire [7:0] img_blue     ;


YCbCr422_2_RGB888 YCbCr422_2_RGB888_u0(   
    //CMOS YCbCr422 data input
    .YCbCr422_vsync  (sar_img_vs	      ),   //Prepared Image data vsync valid signal
    .YCbCr422_hsync  (sar_img_hs	      ),   //Prepared Image data hsync vaild signal
    .YCbCr422_data_en(sar_img_de	      ),  
    .img_Y           (sar_img_data[7:0]	  ),   //Prepared Image data of Y
    .img_CbCr        (sar_img_data[15:8]  ),   //Prepared Image data of CbCr

    //CMOS RGB888 data output
    .RGB888_vsync    (cam_vs              ),   //Processed Image data vsync valid signal
    .RGB888_hsync    (cam_hs              ),   //Processed Image data hsync vaild signal
    .RGB888_data_en  (cam_data_en         ),  
    .img_red         (img_red             ),   //Prepared Image green data to be processed
    .img_green       (img_green           ),   //Prepared Image green data to be processed
    .img_blue        (img_blue            ),   //Prepared Image blue data to be processed
     
    .clk             (sar_img_clk         ),   //cmos video pixel clock
    .rst_n           (rst_n               )    //global reset
);

assign cam_rgb = {img_red,img_green,img_blue};
assign cam_clk = sar_img_clk;


endmodule