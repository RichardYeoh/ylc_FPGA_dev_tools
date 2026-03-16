//////////////////////////////////////////////////////////////////////////
// Copyright@2025 CHINA AERONAUTICS COMPUTING TECHNIQUE RESEARCH INSTITUTE
//                ACTRI-30s Confidential Proprietary
//////////////////////////////////////////////////////////////////////////
// FILE NAME : my_vid_to_axis.v
// TYPE : module 
// DEPARTMENT : Team-30s
// AUTHOR : Yang Licheng
// AUTHOR'S EMAIL : ylcheng@actri.avic1
//////////////////////////////////////////////////////////////////////////
// Release history
// VERSION    Date          AUTHOR            DESCRIPTION
// 1.0        2025-12-17    YangLicheng       File Created
//////////////////////////////////////////////////////////////////////////
// PURPOSE : convert native video timing to axi4-stream. common clk
//////////////////////////////////////////////////////////////////////////
// PARAMETERS
// PARAM NAME   RANGE     : DESCRIPTION           : DEFAULT  : VA UNITS
//////////////////////////////////////////////////////////////////////////
// REUSE ISSUES
// Reset Strategy    : asynchronous, external, HW
// Clock Domains     : <200MHz
// Critical Timing   :
// Test Features     : none
// Asynchronous I/F  : none
// Instantiations    : none
// Other             : none
//////////////////////////////////////////////////////////////////////////
`timescale 1ns / 1ps

module my_vid_to_axis    #(
    parameter     VESA_VTT = 1125          //line Ver Total Time
   ,parameter     VESA_VAT = 1080          //line Ver Addr Time 
   ,parameter     VESA_VFP = 4             //line V Front Porch 
   ,parameter     VESA_VST = 5             //line V Sync Time   
   ,parameter     VESA_VBP = 36            //line V Back Porch  
                                        
   ,parameter     VESA_HTT = 2200          //cycle Hor Total Time
   ,parameter     VESA_HAT = 1920          //cycle Hor Addr Time 
   ,parameter     VESA_HFP = 88            //cycle H Front Porch 
   ,parameter     VESA_HST = 44            //cycle H Sync Time   
   ,parameter     VESA_HBP = 148           //cycle H Back Porch  
   
   ,parameter     VID_DATA_WIDTH = 24
   )
   (
    input                  rst_n         
   ,input                  video_in_clk         
   ,input                  vid_in_vs        //must be high-pulse 
   ,input                  vid_in_hs         
   ,input                  vid_in_de         
   ,input      [VID_DATA_WIDTH-1 : 0]  vid_in_data         
       
   ,input                  m_axis_rdy       //must be always 1
   ,output reg             m_axis_sof       
   ,output reg             m_axis_eol       
   ,output reg             m_axis_valid       
   ,output reg [VID_DATA_WIDTH-1:0] m_axis_data       

 );

reg new_frm_flg;
reg [15:0] pix_cnt;
 
always@(posedge video_in_clk or negedge rst_n) begin
   if (!rst_n) begin
      m_axis_valid <= 1'b0;
      m_axis_data  <= {VID_DATA_WIDTH{1'b0}};
   end else begin
      m_axis_valid <= vid_in_de;
      m_axis_data  <= vid_in_data;
   end
end


always@(posedge video_in_clk or negedge rst_n) begin
   if (!rst_n) begin
      new_frm_flg <= 1'b0;
   end else begin
      if (vid_in_vs) begin
         new_frm_flg <= 1'b1;
      end else begin
         if (m_axis_sof) begin
            new_frm_flg <= 1'b0;
         end else begin
            new_frm_flg <= new_frm_flg;
         end
      end
   end
end

always@(posedge video_in_clk or negedge rst_n) begin
   if (!rst_n) begin
      m_axis_sof <= 1'b0;
   end else begin
      if (new_frm_flg && vid_in_de && ~m_axis_sof) begin
         m_axis_sof <= 1'b1;
      end else begin
         m_axis_sof <= 1'b0;
      end
   end
end

always@(posedge video_in_clk or negedge rst_n) begin
   if (!rst_n) begin
      pix_cnt <= 16'b0;
   end else begin
      if (vid_in_vs || vid_in_hs) begin
         pix_cnt <= 16'b0;
      end else begin
         if (vid_in_de) begin
            pix_cnt <= pix_cnt + 16'b1;
         end else begin
            pix_cnt <= pix_cnt;
         end 
      end
   end
end

always@(posedge video_in_clk or negedge rst_n) begin
   if (~rst_n) begin
      m_axis_eol <= 1'b0;
   end else begin
      if (vid_in_vs || vid_in_hs) begin
         m_axis_eol <= 1'b0;
      end else begin
         if (pix_cnt == VESA_HAT-1) begin
            m_axis_eol <= 1'b1;
         end else begin
            m_axis_eol <= 1'b0;
         end
      end
   end
end


endmodule 