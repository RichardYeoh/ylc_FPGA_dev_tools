//////////////////////////////////////////////////////////////////////////
// Copyright@2018 CHINA AERONAUTICS COMPUTING TECHNIQUE RESEARCH INSTITUTE
//                ACTRI-1s Confidential Proprietary
//////////////////////////////////////////////////////////////////////////
// FILE NAME : mix_single_pal_demo.v
// TYPE : module
// DEPARTMENT : Team-102
// AUTHOR : Yang Licheng
// AUTHOR'S EMAIL : ylcheng@actri.avic1
////////////////////////////////////////////////////////////////////////// 
// Release history 
// VERSION    Date          AUTHOR            DESCRIPTION 
// 1.0        2018-01-31    YangLicheng       File Created
////////////////////////////////////////////////////////////////////////// 
// PURPOSE : VESA Timing Generation
////////////////////////////////////////////////////////////////////////// 
// PARAMETERS 
// PARAM NAME   RANGE     : DESCRIPTION           : DEFAULT  : VA UNITS 
////////////////////////////////////////////////////////////////////////// 
// REUSE ISSUES 
// Reset Strategy    : asynchronous, external, HW  
// Clock Domains     : <200MHz typical:65MHz
// Critical Timing   : refer to VESA Monitor Timing Standard
// Test Features     : none
// Asynchronous I/F  : none
// Instantiations    : none
// Other             : none
//////////////////////////////////////////////////////////////////////////
`timescale 1ns/1ps

module vesa_vtg_dynamic #(
    parameter     VESA_VTT = 1235     ,    //line Ver Total Time
    parameter     VESA_VAT = 1200     ,    //line Ver Addr Time 
    parameter     VESA_VFP = 1        ,    //line V Front Porch 
    parameter     VESA_VST = 3        ,    //line V Sync Time   
    parameter     VESA_VBP = 31       ,    //line V Back Porch  
                                 
    parameter     VESA_HTT = 1728     ,    //cycle Hor Total Time
    parameter     VESA_HAT = 1600     ,    //cycle Hor Addr Time 
    parameter     VESA_HFP = 32       ,    //cycle H Front Porch 
    parameter     VESA_HST = 32       ,    //cycle H Sync Time   
    parameter     VESA_HBP = 64            //cycle H Back Porch  
    )
    (
    input              clk_vesa             ,
    input              rst_n                ,
                                                
    output reg         mix_rd_statu         ,
    
    output reg  [15:0] line_cnt             ,//cnt from 1 to VESA_VTT, start from VST
    output reg  [15:0] pix_cnt              ,//cnt from 1 to VESA_HTT, start from HST
                                                
    output             dvi_out_vs           ,
    output             dvi_out_hs           ,
    output             dvi_out_de           ,
    output      [23:0] dvi_out_data         
    );

///////////////////////////////////////////////
// started from ST
// optimized by ylcheng 2014-09-04
///////////////////////////////////////////////
parameter VESA_VST_E = VESA_VST                      ;//line V Sync Time End Time
parameter VESA_VBP_E = VESA_VST + VESA_VBP           ;//line V Back Porch End Time
parameter VESA_VAT_E = VESA_VST + VESA_VBP + VESA_VAT;//line V Active Time End Time

parameter VESA_HST_E = VESA_HST                      ;//cycle H Sync Time End Time   
parameter VESA_HBP_E = VESA_HST + VESA_HBP           ;//cycle H Back Porch End Time  
parameter VESA_HAT_E = VESA_HST + VESA_HBP + VESA_HAT;//cycle H Active Time End Time   

wire   [ 3:0]     quart_en       ;

reg               sim_vs         ;
reg               sim_hs         ;
reg               sim_de         ;
reg    [23:0]     sim_data       ;

reg               sim_vs_pos        ;
reg               sim_vs_neg        ;
reg               sim_hs_pos        ;
reg               sim_hs_neg        ;
reg               sim_de_pos        ;
reg               sim_de_neg        ;

reg          sim_vs_d1           ;
reg          sim_hs_d1           ;
reg          sim_de_d1           ;
reg  [23:0]  sim_data_d1         ;
reg          sim_vs_d2           ;         
reg          sim_hs_d2           ;         
reg          sim_de_d2           ;         
reg  [23:0]  sim_data_d2         ;         
reg          sim_vs_d3           ;         
reg          sim_hs_d3           ;         
reg          sim_de_d3           ;         
reg  [23:0]  sim_data_d3         ;         
reg          sim_vs_d4           ;         
reg          sim_hs_d4           ;         
reg          sim_de_d4           ;         
reg  [23:0]  sim_data_d4         ;         
reg          sim_vs_d5           ;         
reg          sim_hs_d5           ;         
reg          sim_de_d5           ;         
reg  [23:0]  sim_data_d5         ;      

reg  [ 7:0]  frm_cnt             ;   


//cnt 
always@(posedge clk_vesa or negedge rst_n) begin
  if (~rst_n) begin
    pix_cnt    <= 16'b0          ;
    line_cnt   <= VESA_VTT-500          ;
    frm_cnt    <= 16'b0          ;
  end else begin
    if (line_cnt < VESA_VTT) begin
      if (pix_cnt < VESA_HTT) begin
        pix_cnt  <= pix_cnt + 16'b1;
        line_cnt <= line_cnt       ;
        frm_cnt  <= frm_cnt        ;
      end else begin
        pix_cnt  <= 16'b1           ;
        line_cnt <= line_cnt + 16'b1;
        frm_cnt  <= frm_cnt        ;
      end 
    end  else begin
      if (pix_cnt < VESA_HTT) begin
        pix_cnt  <= pix_cnt + 16'b1;
        line_cnt <= line_cnt       ;
        frm_cnt  <= frm_cnt        ;
      end else begin
        pix_cnt  <= 16'b1          ;
        line_cnt <= 16'b1          ;
        frm_cnt  <= frm_cnt + 1    ;
      end
    end
  end
end 

//generate vs
always@(posedge clk_vesa or negedge rst_n) begin
  if (~rst_n) begin
    sim_vs <= 1'b0;
  end else begin
    if (line_cnt <= VESA_VST_E) begin
      sim_vs <= 1'b1;
    end else begin
      sim_vs <= 1'b0;
    end 
  end 
end 
//generate hs
always@(posedge clk_vesa or negedge rst_n) begin
  if (~rst_n) begin
    sim_hs <= 1'b0;
  end else begin
    if (pix_cnt <= VESA_HST_E) begin
      sim_hs <= 1'b1;
    end else begin
      sim_hs <= 1'b0;
    end 
  end 
end 
//generate simulation data
assign quart_en[0] = ((pix_cnt >   VESA_HBP_E)                
                   && (pix_cnt <= (VESA_HBP_E + VESA_HAT/4))) ? 
                   1'b1 : 1'b0;
                   
assign quart_en[1] = ((pix_cnt >  (VESA_HBP_E + VESA_HAT/4)) 
                   && (pix_cnt <= (VESA_HBP_E + VESA_HAT/2))) ? 
                   1'b1 : 1'b0;
                   
assign quart_en[2] = ((pix_cnt >  (VESA_HBP_E + VESA_HAT/2)) 
                   && (pix_cnt <= (VESA_HBP_E + VESA_HAT/2 + VESA_HAT/4))) ? 
                   1'b1 : 1'b0;
                   
assign quart_en[3] = ((pix_cnt >  (VESA_HBP_E + VESA_HAT/2 + VESA_HAT/4)) 
                   && (pix_cnt <=  VESA_HAT_E)) ? 
                   1'b1 : 1'b0;

always@(posedge clk_vesa or negedge rst_n) begin
  if (~rst_n) begin
    sim_data <= 24'b0;
  end else begin
    if (line_cnt > VESA_VBP_E && line_cnt <= VESA_VAT_E) begin
      case (quart_en) 
          4'b0001: begin
                    sim_data <= 24'hFF0000;
                  end
          4'b0010: begin
                    sim_data <= 24'h00FF00 + {frm_cnt,8'h0};
                  end
          4'b0100: begin
                    sim_data <= 24'h00FFFF;
                  end
          4'b1000: begin
                    sim_data <= 24'h888888 + {frm_cnt,8'h0};
                  end
          default: begin
                    sim_data <= 24'h000000;
                  end
      endcase
    end else begin
      sim_data <= 24'h000000;
    end//line_cnt
  end//rst_n
end//always

//generate de
always@(posedge clk_vesa or negedge rst_n) begin
  if (~rst_n) begin
    sim_de   <= 1'b0;
  end else begin
    if ((line_cnt > VESA_VBP_E && line_cnt <= VESA_VAT_E ) && 
        (pix_cnt  > VESA_HBP_E && pix_cnt  <= VESA_HAT_E)) begin
      sim_de <= 1'b1;
    end else begin
      sim_de <= 1'b0;
    end//line_cnt
  end//rst_n
end//always

//reg delay 
always@(posedge clk_vesa or negedge rst_n) begin
  if (~rst_n) begin
    sim_vs_d1    <= 1'b0           ;
    sim_hs_d1    <= 1'b0           ;
    sim_de_d1    <= 1'b0           ;
    sim_data_d1  <= 24'h000000     ;
    sim_vs_d2    <= 1'b0           ;
    sim_hs_d2    <= 1'b0           ;
    sim_de_d2    <= 1'b0           ;
    sim_data_d2  <= 24'h000000     ;
    sim_vs_d3    <= 1'b0           ;
    sim_hs_d3    <= 1'b0           ;
    sim_de_d3    <= 1'b0           ;
    sim_data_d3  <= 24'h000000     ;
    sim_vs_d4    <= 1'b0           ;
    sim_hs_d4    <= 1'b0           ;
    sim_de_d4    <= 1'b0           ;
    sim_data_d4  <= 24'h000000     ;
    sim_vs_d5    <= 1'b0           ;
    sim_hs_d5    <= 1'b0           ;
    sim_de_d5    <= 1'b0           ;
    sim_data_d5  <= 24'h000000     ;
  end else begin
    sim_vs_d1    <= sim_vs         ;
    sim_hs_d1    <= sim_hs         ;
    sim_de_d1    <= sim_de         ;
    sim_data_d1  <= sim_data       ;
    sim_vs_d2    <= sim_vs_d1      ;
    sim_hs_d2    <= sim_hs_d1      ;
    sim_de_d2    <= sim_de_d1      ;
    sim_data_d2  <= sim_data_d1    ;
    sim_vs_d3    <= sim_vs_d2      ;
    sim_hs_d3    <= sim_hs_d2      ;
    sim_de_d3    <= sim_de_d2      ;
    sim_data_d3  <= sim_data_d2    ;
    sim_vs_d4    <= sim_vs_d3      ;
    sim_hs_d4    <= sim_hs_d3      ;
    sim_de_d4    <= sim_de_d3      ;
    sim_data_d4  <= sim_data_d3    ;
    sim_vs_d5    <= sim_vs_d4      ;
    sim_hs_d5    <= sim_hs_d4      ;
    sim_de_d5    <= sim_de_d4      ;
    sim_data_d5  <= sim_data_d4    ;
  end
end

//other sync flag
always@(posedge clk_vesa or negedge rst_n) begin
  if (~rst_n) begin
    sim_vs_pos        <= 1'b0;
    sim_vs_neg        <= 1'b0;
    sim_hs_pos        <= 1'b0;
    sim_hs_neg        <= 1'b0;
    sim_de_pos        <= 1'b0;
    sim_de_neg        <= 1'b0;
  end else begin
    sim_vs_pos        <= ~sim_vs_d2 &&  sim_vs_d1;
    sim_vs_neg        <=  sim_vs_d2 && ~sim_vs_d1;
    sim_hs_pos        <= ~sim_hs_d2 &&  sim_hs_d1;
    sim_hs_neg        <=  sim_hs_d2 && ~sim_hs_d1;
    sim_de_pos        <= ~sim_de_d2 &&  sim_de_d1;
    sim_de_neg        <=  sim_de_d2 && ~sim_de_d1;
  end//rst_n
end//always

//read statu output
always@(posedge clk_vesa or negedge rst_n) begin
   if (~rst_n) begin
      mix_rd_statu  <= 1'b0;
   end else begin
      if (sim_vs_pos) begin
         mix_rd_statu  <= ~mix_rd_statu;
      end else begin
         mix_rd_statu  <= mix_rd_statu;
      end
   end 
end

assign dvi_out_vs           = sim_vs   ;
assign dvi_out_hs           = sim_hs   ;
assign dvi_out_de           = sim_de   ;
assign dvi_out_data         = sim_data;





endmodule
  
                