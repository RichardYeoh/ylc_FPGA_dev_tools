//==============================================================================
// Orgnization   : Shanghai Fudan Microelectronics Co., Ltd. Confidential
// File Name     : ai7100_top.v
// Author        : Xu Yun
// Project       : NB2014
// Create Date   : 2022.04.10
// Description   :
//------------------------------------------------------------------------------
// Modification History :
// Rev     Date         Who          Description
//==============================================================================
`include"ddr_width.v"
module ai7100_top( 
  // PS
  inout     [53 : 0]     FIXED_IO_0_mio             ,
  inout     [14 : 0]     DDR_0_addr                 ,    
  inout     [2  : 0]     DDR_0_ba                   , 
  inout                  DDR_0_cas_n                , 
  inout                  DDR_0_ck_n                 , 
  inout                  DDR_0_ck_p                 , 
  inout                  DDR_0_cke                  , 
  inout                  DDR_0_cs_n                 , 
  inout     [3  : 0]     DDR_0_dm                   , 
  inout     [31 : 0]     DDR_0_dq                   , 
  inout     [3  : 0]     DDR_0_dqs_n                , 
  inout     [3  : 0]     DDR_0_dqs_p                , 
  inout                  DDR_0_odt                  , 
  inout                  DDR_0_ras_n                , 
  inout                  DDR_0_reset_n              , 
  inout                  DDR_0_we_n                 , 
  inout                  FIXED_IO_0_ddr_vrn         , 
  inout                  FIXED_IO_0_ddr_vrp         , 
  inout                  FIXED_IO_0_ps_clk          ,
  inout                  FIXED_IO_0_ps_porb         ,
  inout                  FIXED_IO_0_ps_srstb        ,
         

	// PL DDR HR 32
    // Inouts                                    
    inout       [31:0]  DDR3_0_dq           ,
    inout       [3:0]   DDR3_0_dqs_n        ,
    inout       [3:0]   DDR3_0_dqs_p        ,
    // Outputs
    output      [15:0]  DDR3_0_addr         ,
    output      [2:0]   DDR3_0_ba           ,
    output              DDR3_0_ras_n        ,
    output              DDR3_0_cas_n        ,
    output              DDR3_0_we_n         ,
    output              DDR3_0_reset_n      ,
    output      [0:0]   DDR3_0_ck_p         ,
    output      [0:0]   DDR3_0_ck_n         ,
    output      [0:0]   DDR3_0_cke          ,
    output      [0:0]   DDR3_0_cs_n         ,
    output      [3:0]   DDR3_0_dm           ,
    output      [0:0]   DDR3_0_odt          ,
       
	input			sys_clk_50m_i					,
	output			TWO_PHY_RSTN					, 
	input 			PJTAG_0_tck         			,
	input 			PJTAG_0_tdi         			,
	output 			PJTAG_0_tdo         			,
	input 			PJTAG_0_tms         			,
	
	output			MDIO_PHY_0_mdc					,
	inout 			MDIO_PHY_0_mdio_io				,

	input [3:0]		RGMII_0_rd          			,
	input 			RGMII_0_rx_ctl      			,
	input 			RGMII_0_rxc         			,
	output [3:0]	RGMII_0_td          			,
	output 			RGMII_0_tx_ctl      			,
	output 			RGMII_0_txc         			,
 
 
   output    [  1 : 0]    led                       ,

// SSD 复位
	output					SSD0_PCIE_RST			,

// PCIE时钟选择	00本地	01连接器
	output					RES_SEL0				,
	output					RES_SEL1				,

// PCIE Interface
   input     [  3 : 0]    pcie_mgt_rxn              ,
   input     [  3 : 0]    pcie_mgt_rxp              ,
   output    [  3 : 0]    pcie_mgt_txn              ,
   output    [  3 : 0]    pcie_mgt_txp              ,
   input                  pcie_sys_clk_p            ,
   input                  pcie_sys_clk_n            ,
   input                  pcie_sys_rst_n              
   
   ,input                  aurora_ref_clk_n
   ,input                  aurora_ref_clk_p
   ,input                  aurora_rx0_n
   ,input                  aurora_rx0_p
   ,output                 aurora_tx0_n
   ,output                 aurora_tx0_p
);


   wire                    clk_200m		           ;
   wire                    clk_250m		           ;
   wire                    clk_27m		           ;
   wire                    clk_100m               ;
   wire                    clk_50m                ;
   wire                    locked		           ;
   
   
   
   
   
    wire               SI570_MGT_CLKP               ;
    wire               SI570_MGT_CLKN               ;
    wire               c2c_reset                    ;
    wire  [  3 : 0]    aurora_rx_p_mas              ;
    wire  [  3 : 0]    aurora_rx_n_mas              ;
    wire  [  3 : 0]    aurora_tx_p_mas              ;
    wire  [  3 : 0]    aurora_tx_n_mas              ;
    wire  [  4 : 0]    PCIE_Switch_sts              ;          


  // ************************************************************************************
  //   BUYI AI
  // ************************************************************************************

    wire          [    31 : 0  ]    gp0_ar_cnt      ;        
    wire          [    31 : 0  ]    gp0_r_cnt       ;        
    wire          [    31 : 0  ]    gp0_aw_cnt      ;           
    wire          [    31 : 0  ]    gp0_w_cnt       ;        
    wire          [    31 : 0  ]    gp0_b_cnt       ;        
   
    wire          [    31 : 0  ]    gp1_ar_cnt      ;        
    wire          [    31 : 0  ]    gp1_r_cnt       ;        
    wire          [    31 : 0  ]    gp1_aw_cnt      ;        
    wire          [    31 : 0  ]    gp1_w_cnt       ;          
    wire          [    31 : 0  ]    gp1_b_cnt       ; 

    wire          [     3 : 0  ]    hp_disable      ; 
  // ************************************************************************************
  //   PS-PL
  // ************************************************************************************
    wire              FCLK_CLK0               ;
    wire              FCLK_RESET0_N           ;

    `ifdef  DDR32
      wire  [32*8-1 : 0]   app_wdf_data       ;
      wire  [32-1   : 0]   app_wdf_mask       ;
      wire  [32*8-1 : 0]   app_rd_data        ; 
    `elsif  DDR64
      wire  [64*8-1 : 0]   app_wdf_data       ;
      wire  [64-1   : 0]   app_wdf_mask       ;
      wire  [64*8-1 : 0]   app_rd_data        ;
    `endif
    wire  [28 : 0 ]   app_addr                ;
    wire  [2 : 0  ]   app_cmd                 ;
    wire              app_en                  ;
    wire              app_wdf_end             ;
    wire              app_wdf_wren            ;
    wire              app_rd_data_end         ; 
    wire              app_rd_data_valid       ; 
    wire              app_rdy                 ; 
    wire              app_wdf_rdy             ; 

  // ************************************************************************************
  //   reset and clocks
  // ************************************************************************************
  wire              soft_rst            ;
  wire              sys_rst_n           ;

  wire              ddr_clk_rst         ;
  wire              gp_clk_rst          ;
  wire              hp_clk_rst          ;

  wire              ps_clk_out          ;  
  wire              ddr_clk             ;

  wire              gp_clk              ;
  wire              hp_clk              ;
  
  wire              ddr_ui_rst          ; // not use
  wire              ddr3_init_done      ;
  wire              ddr_clk_led         ;
  wire              ps_clk_led          ;

  // ************************************************************************************
  //   cam & display
  // ************************************************************************************
  wire              led1                ;
  wire              led2                ;
  wire              led3                ;
  wire              cam_hs              ;
  wire              cam_vs              ;
  wire  [23:0]      cam_rgb             ;
  wire              cam_clk             ;
  wire              cam_data_en         ; 

  wire              cmos_vsync_out      ;
  wire              cmos_href_out       ;
  wire  [23:0]      cmos_db_out         ; 
  wire  [1 :0]      write_addr_index    ;
  wire  [1 :0]      read_addr_index     ;    
  wire              continuous_en       ;
  wire              img_start           ;
  wire  [63:0]      img_data            ;
  wire              img_valid           ;
  wire              img_ready           ;  
  wire              img_start0          ;
  wire  [63:0]      img_data0           ;
  wire              img_valid0          ;
  wire              img_ready0          ;  
  wire              img_start1          ;
  wire  [23:0]      img_plin_data       ;
  wire  [63:0]      img_data1           ;
  wire              img_valid1          ;
  wire              img_ready1          ;
  wire              reset_cam_clk       ;
  wire              network_running     ;  

  wire  [15 : 0]    ps_x0_pos           ;
  wire  [15 : 0]    ps_y0_pos           ;
  wire  [15 : 0]    ps_x1_pos           ;
  wire  [15 : 0]    ps_y1_pos           ;
  wire  [15 : 0]    ps_x_leng           ;
  wire  [15 : 0]    ps_y_leng           ;
  wire  [ 3 : 0]    ps_hstride          ;
  wire  [ 3 : 0]    ps_vstride          ;
  wire  [10 : 0]    resize_pix_len      ;
  wire  [31 : 0]    write_ps_size       ;
  wire              display_en          ;

  wire  [31 : 0]    camera_wr_addr      ;
  wire  [31 : 0]    camera_rd_addr      ;
  wire              wr_done_pulse       ;
     
  wire              wr_wfifo_err        ;
  wire              rd_rfifo_err        ;
  wire              dip_switches        ;
  wire              si5368_rst_n        ;
  wire  [31 : 0]    c2c_status          ;
  wire              pcie_link_up        ;
  wire              clk_125m            ;
  wire              clk_125m_rstn       ;
  wire              pcie_sys_clk        ;

  wire  [3:0]       PCIE_S_AXI_AWID              ;
  wire  [63:0]      PCIE_S_AXI_AWADDR            ;
  wire  [7:0]       PCIE_S_AXI_AWLEN             ;
  wire  [2:0]       PCIE_S_AXI_AWSIZE            ;
  wire  [1:0]       PCIE_S_AXI_AWBURST           ;
  wire              PCIE_S_AXI_AWLOCK            ;
  wire  [3:0]       PCIE_S_AXI_AWCACHE           ;
  wire  [2:0]       PCIE_S_AXI_AWPROT            ;
  wire  [3:0]       PCIE_S_AXI_AWQOS             ;
  wire              PCIE_S_AXI_AWVALID           ;
  wire              PCIE_S_AXI_AWREADY           ;
  wire  [127:0]     PCIE_S_AXI_WDATA             ;
  wire  [15:0]      PCIE_S_AXI_WSTRB             ;
  wire              PCIE_S_AXI_WLAST             ;
  wire              PCIE_S_AXI_WVALID            ;
  wire              PCIE_S_AXI_WREADY            ;
  wire  [3:0]       PCIE_S_AXI_BID               ;
  wire  [1:0]       PCIE_S_AXI_BRESP             ;
  wire              PCIE_S_AXI_BVALID            ;
  wire              PCIE_S_AXI_BREADY            ;
  wire  [3:0]       PCIE_S_AXI_ARID              ;
  wire  [63:0]      PCIE_S_AXI_ARADDR            ;
  wire  [7:0]       PCIE_S_AXI_ARLEN             ;
  wire  [2:0]       PCIE_S_AXI_ARSIZE            ;
  wire  [1:0]       PCIE_S_AXI_ARBURST           ;
  wire              PCIE_S_AXI_ARLOCK            ;
  wire  [3:0]       PCIE_S_AXI_ARCACHE           ;
  wire  [2:0]       PCIE_S_AXI_ARPROT            ;
  wire              PCIE_S_AXI_ARQOS             ;
  wire              PCIE_S_AXI_ARVALID           ;
  wire              PCIE_S_AXI_ARREADY           ;
  wire  [3:0]       PCIE_S_AXI_RID               ;
  wire  [127:0]     PCIE_S_AXI_RDATA             ;
  wire  [1:0]       PCIE_S_AXI_RRESP             ;
  wire              PCIE_S_AXI_RLAST             ;
  wire              PCIE_S_AXI_RVALID            ;
  wire              PCIE_S_AXI_RREADY            ; 

  wire	[31:0]		M02_AXI_0_araddr    		;
  wire	[1:0]		M02_AXI_0_arburst   		;
  wire	[3:0]		M02_AXI_0_arcache   		;
  wire	[11:0]		M02_AXI_0_arid      		;
  wire	[7:0]		M02_AXI_0_arlen     		;
  wire	[0:0]		M02_AXI_0_arlock    		;
  wire	[2:0]		M02_AXI_0_arprot    		;
  wire	[3:0]		M02_AXI_0_arqos     		;
  wire				M02_AXI_0_arready   		;
  wire	[3:0]		M02_AXI_0_arregion  		;
  wire	[2:0]		M02_AXI_0_arsize    		;
  wire				M02_AXI_0_arvalid   		;
  wire	[31:0]		M02_AXI_0_awaddr    		;
  wire	[1:0]		M02_AXI_0_awburst   		;
  wire	[3:0]		M02_AXI_0_awcache   		;
  wire	[11:0]		M02_AXI_0_awid      		;
  wire	[7:0]		M02_AXI_0_awlen     		;
  wire	[0:0]		M02_AXI_0_awlock    		;
  wire	[2:0]		M02_AXI_0_awprot    		;
  wire	[3:0]		M02_AXI_0_awqos     		;
  wire				M02_AXI_0_awready   		;
  wire	[3:0]		M02_AXI_0_awregion  		;
  wire	[2:0]		M02_AXI_0_awsize    		;
  wire				M02_AXI_0_awvalid   		;
  wire	[11:0]		M02_AXI_0_bid       		;
  wire				M02_AXI_0_bready    		;
  wire	[1:0]		M02_AXI_0_bresp     		;
  wire				M02_AXI_0_bvalid    		;
  wire	[31:0]		M02_AXI_0_rdata     		;
  wire	[11:0]		M02_AXI_0_rid       		;
  wire				M02_AXI_0_rlast     		;
  wire 				M02_AXI_0_rready    		;
  wire	[1:0]		M02_AXI_0_rresp     		;
  wire				M02_AXI_0_rvalid    		;
  wire 	[31:0]		M02_AXI_0_wdata     		;
  wire 				M02_AXI_0_wlast     		;
  wire				M02_AXI_0_wready    		;
  wire	[3:0]		M02_AXI_0_wstrb     		;
  wire				M02_AXI_0_wvalid			;

  wire  [ 31 : 0]   PCIE_S_AXI_GP0_araddr        ;
  wire  [  2 : 0]   PCIE_S_AXI_GP0_arprot        ;
  wire              PCIE_S_AXI_GP0_arready       ;
  wire              PCIE_S_AXI_GP0_arvalid       ;
  wire  [ 31 : 0]   PCIE_S_AXI_GP0_awaddr        ;
  wire  [  2 : 0]   PCIE_S_AXI_GP0_awprot        ;
  wire              PCIE_S_AXI_GP0_awready       ;
  wire              PCIE_S_AXI_GP0_awvalid       ;
  wire              PCIE_S_AXI_GP0_bready        ;
  wire  [  1 : 0]   PCIE_S_AXI_GP0_bresp         ;
  wire              PCIE_S_AXI_GP0_bvalid        ;
  wire  [ 31 : 0]   PCIE_S_AXI_GP0_rdata         ;
  wire              PCIE_S_AXI_GP0_rready        ;
  wire  [  1 : 0]   PCIE_S_AXI_GP0_rresp         ;
  wire              PCIE_S_AXI_GP0_rvalid        ;
  wire  [ 31 : 0]   PCIE_S_AXI_GP0_wdata         ;
  wire              PCIE_S_AXI_GP0_wready        ;
  wire  [  3 : 0]   PCIE_S_AXI_GP0_wstrb         ;
  wire              PCIE_S_AXI_GP0_wvalid        ;   

  wire  [ 15 : 0]   usr_irq_req                  	;
  wire  [ 15 : 0]   usr_irq_ack                  	;
  wire              msi_enable                   	;
  wire  [  2 : 0]   msi_vector_width             	;  
  wire              test_irq           				;
  wire              customop_irq       				;
  wire              ai_irq             				;   
  wire              sys_rst        					;

	//ddr3 HR
   wire              pl_hr_ddr_clk       ;
(* dont_touch="true" *)(* MARK_DEBUG="true" *)   wire              pl_mig_ui_rst_n     ;
   
(* dont_touch="true" *)(* MARK_DEBUG="true" *)   wire              user_lnk_up_0;

(* dont_touch="true" *)(* MARK_DEBUG="true" *)	wire                  ddr_mmcm_locked			;
(* dont_touch="true" *)(* MARK_DEBUG="true" *)	wire                  ddr3_init_done_hr			;
	wire                  ui_clk					;
  

	
	//////////////sar aurora////////////////////////
   wire              sar_rx_clk;
   wire              sar_rx_sys_rst;
(* dont_touch="true" *)(* MARK_DEBUG="true" *)   wire     [31: 0]  sar_rx_tdata;
(* dont_touch="true" *)(* MARK_DEBUG="true" *)   wire     [ 3: 0]  sar_rx_tkeep;
(* dont_touch="true" *)(* MARK_DEBUG="true" *)   wire              sar_rx_tlast;
(* dont_touch="true" *)(* MARK_DEBUG="true" *)   wire              sar_rx_tvalid;

   wire              aurora0_hard_err;
   wire              aurora0_soft_err;
   wire              aurora0_frame_err;
   wire              aurora0_channel_up;
   wire              aurora0_lane_up;
   wire              aurora0_tx_lock;
   wire              aurora0_tx_resetdone;
   wire              aurora0_rx_resetdone;
   wire              aurora0_pll_not_locked_out;
	
  /////////////////////////////sar_proc here/////////////////////////////////

  
        wire [31:0]M_AXIS_S2MM_STS_head_tdata;
        wire [3:0]M_AXIS_S2MM_STS_head_tkeep;
        wire M_AXIS_S2MM_STS_head_tlast;     
        wire M_AXIS_S2MM_STS_head_tready;     
        wire M_AXIS_S2MM_STS_head_tvalid;    
         
        wire [71:0]S_AXIS_S2MM_CMD_head_tdata; 
        wire S_AXIS_S2MM_CMD_head_tready;     
        wire S_AXIS_S2MM_CMD_head_tvalid;      
        wire [31:0]S_AXIS_S2MM_head_tdata;     
        wire [3:0]S_AXIS_S2MM_head_tkeep;      
        wire S_AXIS_S2MM_head_tlast;           
        wire S_AXIS_S2MM_head_tready;         
        wire S_AXIS_S2MM_head_tvalid;          
         
        wire [31:0]M_AXIS_S2MM_STS_img_tdata;
        wire [3:0]M_AXIS_S2MM_STS_img_tkeep;
        wire M_AXIS_S2MM_STS_img_tlast;     
        wire M_AXIS_S2MM_STS_img_tready;     
        wire M_AXIS_S2MM_STS_img_tvalid;    
         
        wire [71:0]S_AXIS_S2MM_CMD_img_tdata; 
        wire S_AXIS_S2MM_CMD_img_tready;     
        wire S_AXIS_S2MM_CMD_img_tvalid;      
        wire [31:0]S_AXIS_S2MM_img_tdata;     
        wire [3:0]S_AXIS_S2MM_img_tkeep;      
        wire S_AXIS_S2MM_img_tlast;           
        wire S_AXIS_S2MM_img_tready;         
        wire S_AXIS_S2MM_img_tvalid;          
                 
        wire               sar_img_vs             ;
        wire               sar_img_hs             ;
        wire               sar_img_de             ;
        wire      [15:0]   sar_img_data           ;

        wire      [31:0]   sar_info_buf_addr        ; 
        wire               sar_info_buf_clk         ;       
        wire      [31:0]   sar_info_buf_din         ; 
        wire      [31:0]   sar_info_buf_dout        ; 
        wire               sar_info_buf_en          ;       
        wire               sar_info_buf_rst         ;       
        wire      [ 3:0]   sar_info_buf_we          ;  
  /////////////////////////////sar_proc end/////////////////////////////////
	
	

  mna_gp_ww_itf  ps_gp0();
  mna_gp_ww_itf  ps_gp1();
  mna_gp_ww_itf  gp0();
  mna_gp_ww_itf  gp1();
  mna_hp_std_itf hp0();
  mna_hp_std_itf hp1();
  mna_hp_std_itf hp2();
  mna_hp_std_itf hp3(); 

  mna_gp_ww_itf  host_ctrl()  ;
  mna_gp_ww_itf  ai_ra()      ;
  mna_gp_ww_itf  cam()        ;
  mna_gp_ww_itf  m3_gpx()     ;

  mna_gp_ww_itf  cdma_ctrl()  ;
  mna_gp_ww_itf  cam_gp1_s01();
  mna_gp_ww_itf  cam_gp1_s02();
  mna_gp_ww_itf  cam_gp1_s03();

  mna_ddr_rd_itf img_ddr_rd_itf();  
  mna_gp_ww_itf  pcie_user_gp0()      ;
  mna_gp_ww_itf  pcie_user_gp1()      ; 
  mna_ddr_rd_itf pcie_ps_rd_itf()     ;
  mna_ddr_ww_itf pcie_ps_ww_itf()     ;   
  assign sys_rst = 1'b0;
  assign sys_rst_n    = ~sys_rst                   ;
  assign led[0]     = ddr3_init_done & ddr_clk_led ;
  assign led[1]     = pcie_link_up                 ;
//  assign led[2]     = c2c_status[0]                ;
//  assign led[3]     = c2c_status[1] | c2c_status[2];

  assign dip_switches = 1'b1;

assign SSD0_PCIE_RST = 1 ;
assign RES_SEL0 = 0 ;
assign RES_SEL1 = 0 ;

clk_wiz_1	clk_wiz_1
(
	.clk_out1	(	clk_200m		),    
	.clk_out2	(	clk_250m		),    
	.clk_out3	(	clk_27m		    ),    
   .clk_100m_out(  clk_100m),     // output clk_100m_out
   .clk_50m_out(  clk_50m),     // output clk_50m_out
	.locked		(	locked			),       
	.clk_in1	(	sys_clk_50m_i	)
);   


demo_clkrst_wrapper u_demo_clkrst_wrapper(
  .ddr_clk_led   (ddr_clk_led    ),
  .ps_clk_led    (ps_clk_led     ),
     
  .sys_rst       (sys_rst | (~FCLK_RESET0_N)),
  .soft_rst      (soft_rst       ),

  .ddr_clk       (ddr_clk        ),
  .ps_clk_out    (ps_clk_out     ),
     
  .gp_clk        (gp_clk         ),
  .hp_clk        (hp_clk         ),
  .gp_clk_rst    (gp_clk_rst     ),
  .hp_clk_rst    (hp_clk_rst     ),
  .ddr_clk_rst   (ddr_clk_rst    )
);

////////////////////my_loopback_test///////////////////////////////////////
    wire dvi_vs;
    wire dvi_hs;
    wire dvi_de;
    wire [23:0] dvi_data;

    wire sar_sim_rdy;
    wire sar_sim_sof;
    wire sar_sim_eol;
    wire sar_sim_valid;
    wire [23:0] sar_sim_data;

   vesa_vtg_dynamic #(
       .VESA_VTT           (1125    )    
      ,.VESA_VAT           (1080    )
      ,.VESA_VFP           (4       )
      ,.VESA_VST           (5       )
      ,.VESA_VBP           (36      )
                                
      ,.VESA_HTT           (2200    )
      ,.VESA_HAT           (1920    )
      ,.VESA_HFP           (88      )
      ,.VESA_HST           (44      )
      ,.VESA_HBP           (148     )  
      
      )u_vesa_vtg
      (
       .clk_vesa             (clk_50m)    
      ,.rst_n                (locked)
   
      ,.mix_rd_statu         ( )
   
      ,.line_cnt             ( )
      ,.pix_cnt              ( )
   
      ,.dvi_out_vs           (dvi_vs)
      ,.dvi_out_hs           (dvi_hs)
      ,.dvi_out_de           (dvi_de)
      ,.dvi_out_data         (dvi_data)
       );

   my_vid_to_axis #(
       .VESA_VTT           (1125    )    
      ,.VESA_VAT           (1080    )
      ,.VESA_VFP           (4       )
      ,.VESA_VST           (5       )
      ,.VESA_VBP           (36      )
                                
      ,.VESA_HTT           (2200    )
      ,.VESA_HAT           (1920    )
      ,.VESA_HFP           (88      )
      ,.VESA_HST           (44      )
      ,.VESA_HBP           (148     )  
      
      )u_vesa_to_axis
      (
       .video_in_clk             (clk_50m)    
      ,.rst_n                (locked)
   
      ,.vid_in_vs           (dvi_vs)
      ,.vid_in_hs           (dvi_hs)
      ,.vid_in_de           (dvi_de)
      ,.vid_in_data         (dvi_data)
   
      ,.m_axis_rdy           (sar_sim_rdy)
      ,.m_axis_sof           (sar_sim_sof)
      ,.m_axis_eol           (sar_sim_eol)
      ,.m_axis_valid         (sar_sim_valid)
      ,.m_axis_data          (sar_sim_data)
       );

/////////////////////my_loopback_test///////////////////////////////////////////

///////////////////////////////////////sar aurora////////////////////////////
aurora_8b10b_0 sar_aurora_in (
  
  .reset(!locked),                                      // input wire reset
  .gt_reset(!locked),                                // input wire gt_reset

  .tx_resetdone_out(aurora0_tx_resetdone),                // output wire tx_resetdone_out
  .rx_resetdone_out(aurora0_rx_resetdone),                // output wire rx_resetdone_out

  .drpclk_in(clk_100m),                              // input wire drpclk_in
  .init_clk_in(clk_50m),
  
  .gt_refclk1_p(aurora_ref_clk_p),                        // input wire gt_refclk1_p
  .gt_refclk1_n(aurora_ref_clk_n),                        // input wire gt_refclk1_n

   //usr Interface
  .user_clk_out(sar_rx_clk),                        // output wire user_clk_out
  .sys_reset_out(sar_rx_sys_rst),                      // output wire sys_reset_out

   //tx channel
  .s_axi_tx_tdata({sar_sim_data[7:0],sar_sim_data}),                    // input wire [0 : 31] s_axi_tx_tdata
  .s_axi_tx_tkeep(4'b1111),                    // input wire [0 : 3] s_axi_tx_tkeep
  .s_axi_tx_tlast(sar_sim_eol),                    // input wire s_axi_tx_tlast
  .s_axi_tx_tvalid(sar_sim_valid),                  // input wire s_axi_tx_tvalid
  .s_axi_tx_tready(sar_sim_rdy),                  // output wire s_axi_tx_tready
  
  .txp(aurora_tx0_p),                                          // output wire [0 : 0] txp
  .txn(aurora_tx0_n),                                          // output wire [0 : 0] txn

   //rx channel
  .m_axi_rx_tdata(sar_rx_tdata),                    // output wire [0 : 31] m_axi_rx_tdata
  .m_axi_rx_tkeep(sar_rx_tkeep),                    // output wire [0 : 3] m_axi_rx_tkeep
  .m_axi_rx_tlast(sar_rx_tlast),                    // output wire m_axi_rx_tlast
  .m_axi_rx_tvalid(sar_rx_tvalid),                  // output wire m_axi_rx_tvalid
  .rxp(aurora_rx0_p),                                          // input wire [0 : 0] rxp
  .rxn(aurora_rx0_n),                                          // input wire [0 : 0] rxn

   //statu signal
  .hard_err(aurora0_hard_err),                                // output wire hard_err
  .soft_err(aurora0_soft_err),                                // output wire soft_err
  .frame_err(aurora0_frame_err),                              // output wire frame_err
  .channel_up(aurora0_channel_up),                            // output wire channel_up
  .lane_up(aurora0_lane_up),                                  // output wire [0 : 0] lane_up
  .tx_lock(aurora0_tx_lock),                                  // output wire tx_lock
  .pll_not_locked_out(aurora0_pll_not_locked_out),            // output wire pll_not_locked_out

   //default config
  .loopback(3'b0),                                // input wire [2 : 0] loopback
  .drpaddr_in(9'h0),                            // input wire [8 : 0] drpaddr_in
  .drpen_in(1'b0),                                // input wire drpen_in
  .drpdi_in(16'h0),                                // input wire [15 : 0] drpdi_in
  .drprdy_out( ),                            // output wire drprdy_out
  .drpdo_out( ),                              // output wire [15 : 0] drpdo_out
  .drpwe_in(1'b0),                                // input wire drpwe_in
  .power_down(1'b0),                            // input wire power_down

   //share resources
  .link_reset_out( ),                    // output wire link_reset_out
  .sync_clk_out( ),                        // output wire sync_clk_out
  .gt_reset_out( ),                        // output wire gt_reset_out
  .gt_refclk1_out( ),                    // output wire gt_refclk1_out
  .gt0_qplllock_out( ),                // output wire gt0_qplllock_out
  .gt0_qpllrefclklost_out( ),    // output wire gt0_qpllrefclklost_out
  .gt_qpllclk_quad1_out( ),        // output wire gt_qpllclk_quad1_out
  .gt_qpllrefclk_quad1_out( )  // output wire gt_qpllrefclk_quad1_out
);

sar_proc_top #(
    .C_ORI_DATA_WIDTH         (32            )// DATA bus width                                   
   ,.C_ORI_STRB_WIDTH         (4             )// STROBE bus width                                  
                                                                                       
   ,.FRM_HD                   (32'hEB900400  )// sar frame head                         
   ,.FRM_TYPE_HEAD            (8'h13         )// indicate that this frame is head frame 
   ,.HEAD_MEN_BADDR           (32'h1E000000  )// 0-1E000000(480MB) for image data       
   ,.HEAD_MOVER_TAG           (4'h1          )// 1-head tag; 2-img tag                  
   ,.FRM_TYPE_IMG             (8'h19         )// indicate that this frame is image frame
   ,.IMG_MEN_BADDR            (32'h00000000  )// 0-1E000000(480MB) for image data       
   ,.IMG_MOVER_TAG            (4'h2          )// 1-head tag; 2-img tag                  
   
)u_sar_proc (
    .clk_sys_in               (clk_200m)     // not used
   ,.rst_sys_n                (locked)      // not used
   
   ,.aurora_clk               (sar_rx_clk)                    
   ,.aurora_rst               (sar_rx_sys_rst)                     
   ,.channel_up               (aurora0_channel_up)   
                   
   ,.vid_out_vs               (sar_img_vs             )                     
   ,.vid_out_hs               (sar_img_hs             )                     
   ,.vid_out_de               (sar_img_de             )                     
   ,.vid_out_data             (sar_img_data           )                     
                      
   ,.axi4_s_ip_tx_tdata       (sar_rx_tdata )                     
   ,.axi4_s_ip_tx_tkeep       (sar_rx_tkeep )                     
   ,.axi4_s_ip_tx_tvalid      (sar_rx_tvalid)                     
   ,.axi4_s_ip_tx_tlast       (sar_rx_tlast )                     
   ,.axi4_s_ip_tx_tready      ( )  //nc to aurora keep 1
                      
   ,.mig_ui_clk               (pl_hr_ddr_clk )                     
   ,.mig_rst_n                (pl_mig_ui_rst_n )     
                   
   ,.M_AXIS_S2MM_STS_head_tdata     (M_AXIS_S2MM_STS_head_tdata      )
   ,.M_AXIS_S2MM_STS_head_tkeep     (M_AXIS_S2MM_STS_head_tkeep      )                    
   ,.M_AXIS_S2MM_STS_head_tlast     (M_AXIS_S2MM_STS_head_tlast      )                    
   ,.M_AXIS_S2MM_STS_head_tready    (M_AXIS_S2MM_STS_head_tready     )                    
   ,.M_AXIS_S2MM_STS_head_tvalid    (M_AXIS_S2MM_STS_head_tvalid     )                    

   ,.S_AXIS_S2MM_CMD_head_tdata     (S_AXIS_S2MM_CMD_head_tdata)
   ,.S_AXIS_S2MM_CMD_head_tready    (S_AXIS_S2MM_CMD_head_tready)   
   ,.S_AXIS_S2MM_CMD_head_tvalid    (S_AXIS_S2MM_CMD_head_tvalid)   
   ,.S_AXIS_S2MM_head_tdata         (S_AXIS_S2MM_head_tdata)             
   ,.S_AXIS_S2MM_head_tkeep         (S_AXIS_S2MM_head_tkeep)             
   ,.S_AXIS_S2MM_head_tlast         (S_AXIS_S2MM_head_tlast)             
   ,.S_AXIS_S2MM_head_tready        (S_AXIS_S2MM_head_tready)           
   ,.S_AXIS_S2MM_head_tvalid        (S_AXIS_S2MM_head_tvalid)           
    
   ,.M_AXIS_S2MM_STS_img_tdata      (M_AXIS_S2MM_STS_img_tdata       )
   ,.M_AXIS_S2MM_STS_img_tkeep      (M_AXIS_S2MM_STS_img_tkeep       )                    
   ,.M_AXIS_S2MM_STS_img_tlast      (M_AXIS_S2MM_STS_img_tlast       )                    
   ,.M_AXIS_S2MM_STS_img_tready     (M_AXIS_S2MM_STS_img_tready      )                    
   ,.M_AXIS_S2MM_STS_img_tvalid     (M_AXIS_S2MM_STS_img_tvalid      )                    
                                    
   ,.S_AXIS_S2MM_CMD_img_tdata      (S_AXIS_S2MM_CMD_img_tdata)
   ,.S_AXIS_S2MM_CMD_img_tready     (S_AXIS_S2MM_CMD_img_tready)   
   ,.S_AXIS_S2MM_CMD_img_tvalid     (S_AXIS_S2MM_CMD_img_tvalid)   
   ,.S_AXIS_S2MM_img_tdata          (S_AXIS_S2MM_img_tdata)             
   ,.S_AXIS_S2MM_img_tkeep          (S_AXIS_S2MM_img_tkeep)             
   ,.S_AXIS_S2MM_img_tlast          (S_AXIS_S2MM_img_tlast)             
   ,.S_AXIS_S2MM_img_tready         (S_AXIS_S2MM_img_tready)           
   ,.S_AXIS_S2MM_img_tvalid         (S_AXIS_S2MM_img_tvalid)           
    
   ,.sar_info_buf_addr              (sar_info_buf_addr)                      
   ,.sar_info_buf_clk               (sar_info_buf_clk)                        
   ,.sar_info_buf_din               (sar_info_buf_din)                        
   ,.sar_info_buf_dout              (sar_info_buf_dout)                      
   ,.sar_info_buf_en                (sar_info_buf_en)                          
   ,.sar_info_buf_rst               (sar_info_buf_rst)                        
   ,.sar_info_buf_we                (sar_info_buf_we)                          
  
); 





///////////////////////////////////////sar aurora end////////////////////////////

rx_sdi rx_sdi_inst (
    .rst_n                      (!sar_rx_sys_rst          ),   
    
	//sar img input
	.sar_img_clk            (pl_hr_ddr_clk          ),
	.sar_img_vs             (sar_img_vs             ),
	.sar_img_hs             (sar_img_hs             ),
	.sar_img_de             (sar_img_de             ),
	.sar_img_data           (sar_img_data           ),	

    .cam_hs                     (cam_hs                   ),
    .cam_vs                     (cam_vs                   ),
    .cam_rgb	                 (cam_rgb                  ),
    .cam_clk                    (cam_clk                  ),
    .cam_data_en                (cam_data_en              )
);


my_ps_ai_wrapper ps_ai_wrapper_u0 (



    // .UART_0_0_rxd(UART_0_0_rxd),
    // .UART_0_0_txd(UART_0_0_txd),
    // .UART_1_0_rxd(UART_1_0_rxd),
    // .UART_1_0_txd(UART_1_0_txd),

	.RGMII_0_rd(RGMII_0_rd),
	.RGMII_0_rx_ctl(RGMII_0_rx_ctl),
	.RGMII_0_rxc(RGMII_0_rxc),
	.RGMII_0_td(RGMII_0_td),
	.RGMII_0_tx_ctl(RGMII_0_tx_ctl),
	.RGMII_0_txc(RGMII_0_txc),

	.MDIO_PHY_0_mdc(MDIO_PHY_0_mdc),
	.MDIO_PHY_0_mdio_io(MDIO_PHY_0_mdio_io),

	.PJTAG_0_tck               	(PJTAG_0_tck            ),
	.PJTAG_0_tdi               	(PJTAG_0_tdi            ),
	.PJTAG_0_tdo               	(PJTAG_0_tdo            ),
	.PJTAG_0_tms               	(PJTAG_0_tms            ),

        //ddr	
        .DDR3_0_addr                    (DDR3_0_addr						),
        .DDR3_0_ba                      (DDR3_0_ba							),
        .DDR3_0_cas_n                   (DDR3_0_cas_n						),
        .DDR3_0_ck_n                    (DDR3_0_ck_n						),
        .DDR3_0_ck_p                    (DDR3_0_ck_p						),
        .DDR3_0_cke                     (DDR3_0_cke							),
        .DDR3_0_cs_n                    (DDR3_0_cs_n						),
        .DDR3_0_dm                      (DDR3_0_dm							),
        .DDR3_0_dq                      (DDR3_0_dq							),
        .DDR3_0_dqs_n                   (DDR3_0_dqs_n						),
        .DDR3_0_dqs_p                   (DDR3_0_dqs_p						),
        .DDR3_0_odt                     (DDR3_0_odt							),
        .DDR3_0_ras_n                   (DDR3_0_ras_n						),
        .DDR3_0_reset_n                 (DDR3_0_reset_n						),
        .DDR3_0_we_n                    (DDR3_0_we_n						),
        .ddr_mmcm_locked                (ddr_mmcm_locked					),
        .init_calib_complete            (ddr3_init_done_hr					),
			                                 
        
        .sys_clk_i_0                    (clk_200m),
        .ui_clk                         (pl_hr_ddr_clk),
        .mig_ui_rst_n                   (pl_mig_ui_rst_n),        //  output [0:0]mig_ui_rst_n;
		
        .pcie_mgt_0_rxn					(pcie_mgt_rxn),
        .pcie_mgt_0_rxp					(pcie_mgt_rxp),
        .pcie_mgt_0_txn					(pcie_mgt_txn),
        .pcie_mgt_0_txp					(pcie_mgt_txp),
        .pcie_ref_clk_clk_n				(pcie_sys_clk_n),
        .pcie_ref_clk_clk_p				(pcie_sys_clk_p),
        // .pcie_rst_n						(pcie_sys_rst_n),		
        .user_lnk_up_0					(user_lnk_up_0),	

  /////////////////////////////sar_proc here/////////////////////////////////

  
        .M_AXIS_S2MM_STS_head_tdata(M_AXIS_S2MM_STS_head_tdata),      //output [31:0]M_AXIS_S2MM_STS_head_tdata;
        .M_AXIS_S2MM_STS_head_tkeep(M_AXIS_S2MM_STS_head_tkeep),      //output [3:0]M_AXIS_S2MM_STS_head_tkeep;
        .M_AXIS_S2MM_STS_head_tlast(M_AXIS_S2MM_STS_head_tlast),      //output M_AXIS_S2MM_STS_head_tlast;     
        .M_AXIS_S2MM_STS_head_tready(M_AXIS_S2MM_STS_head_tready),    //input M_AXIS_S2MM_STS_head_tready;     
        .M_AXIS_S2MM_STS_head_tvalid(M_AXIS_S2MM_STS_head_tvalid),    //output M_AXIS_S2MM_STS_head_tvalid;    
  
        .S_AXIS_S2MM_CMD_head_tdata(S_AXIS_S2MM_CMD_head_tdata),      //  input [71:0]S_AXIS_S2MM_CMD_head_tdata; 
        .S_AXIS_S2MM_CMD_head_tready(S_AXIS_S2MM_CMD_head_tready),    //  output S_AXIS_S2MM_CMD_head_tready;     
        .S_AXIS_S2MM_CMD_head_tvalid(S_AXIS_S2MM_CMD_head_tvalid),    //  input S_AXIS_S2MM_CMD_head_tvalid;      
        .S_AXIS_S2MM_head_tdata(S_AXIS_S2MM_head_tdata),              //  input [31:0]S_AXIS_S2MM_head_tdata;     
        .S_AXIS_S2MM_head_tkeep(S_AXIS_S2MM_head_tkeep),              //  input [3:0]S_AXIS_S2MM_head_tkeep;      
        .S_AXIS_S2MM_head_tlast(S_AXIS_S2MM_head_tlast),              //  input S_AXIS_S2MM_head_tlast;           
        .S_AXIS_S2MM_head_tready(S_AXIS_S2MM_head_tready),            //  output S_AXIS_S2MM_head_tready;         
        .S_AXIS_S2MM_head_tvalid(S_AXIS_S2MM_head_tvalid),            //  input S_AXIS_S2MM_head_tvalid;          
  
        .M_AXIS_S2MM_STS_img_tdata(M_AXIS_S2MM_STS_img_tdata),      //output [31:0]M_AXIS_S2MM_STS_img_tdata;
        .M_AXIS_S2MM_STS_img_tkeep(M_AXIS_S2MM_STS_img_tkeep),      //output [3:0]M_AXIS_S2MM_STS_img_tkeep;
        .M_AXIS_S2MM_STS_img_tlast(M_AXIS_S2MM_STS_img_tlast),      //output M_AXIS_S2MM_STS_img_tlast;     
        .M_AXIS_S2MM_STS_img_tready(M_AXIS_S2MM_STS_img_tready),    //input M_AXIS_S2MM_STS_img_tready;     
        .M_AXIS_S2MM_STS_img_tvalid(M_AXIS_S2MM_STS_img_tvalid),    //output M_AXIS_S2MM_STS_img_tvalid;    
  
        .S_AXIS_S2MM_CMD_img_tdata(S_AXIS_S2MM_CMD_img_tdata),      //  input [71:0]S_AXIS_S2MM_CMD_img_tdata; 
        .S_AXIS_S2MM_CMD_img_tready(S_AXIS_S2MM_CMD_img_tready),    //  output S_AXIS_S2MM_CMD_img_tready;     
        .S_AXIS_S2MM_CMD_img_tvalid(S_AXIS_S2MM_CMD_img_tvalid),    //  input S_AXIS_S2MM_CMD_img_tvalid;      
        .S_AXIS_S2MM_img_tdata(S_AXIS_S2MM_img_tdata),              //  input [31:0]S_AXIS_S2MM_img_tdata;     
        .S_AXIS_S2MM_img_tkeep(S_AXIS_S2MM_img_tkeep),              //  input [3:0]S_AXIS_S2MM_img_tkeep;      
        .S_AXIS_S2MM_img_tlast(S_AXIS_S2MM_img_tlast),              //  input S_AXIS_S2MM_img_tlast;           
        .S_AXIS_S2MM_img_tready(S_AXIS_S2MM_img_tready),            //  output S_AXIS_S2MM_img_tready;         
        .S_AXIS_S2MM_img_tvalid(S_AXIS_S2MM_img_tvalid),            //  input S_AXIS_S2MM_img_tvalid;          
  

        .sar_info_buf_addr(sar_info_buf_addr),                        //  input [31:0]sar_info_buf_addr; 
        .sar_info_buf_clk(sar_info_buf_clk),                          //  input sar_info_buf_clk;        
        .sar_info_buf_din(sar_info_buf_din),                          //  input [31:0]sar_info_buf_din;  
        .sar_info_buf_dout(sar_info_buf_dout),                        //  output [31:0]sar_info_buf_dout;
        .sar_info_buf_en(sar_info_buf_en),                            //  input sar_info_buf_en;         
        .sar_info_buf_rst(sar_info_buf_rst),                          //  input sar_info_buf_rst;        
        .sar_info_buf_we(sar_info_buf_we),                            //  input [3:0]sar_info_buf_we;    
  


  /////////////////////////////sar_proc end/////////////////////////////////

    .FIXED_IO_mio              (FIXED_IO_0_mio         ),
    .FIXED_IO_ps_srstb         (FIXED_IO_0_ps_srstb    ),
    .FIXED_IO_ps_clk           (FIXED_IO_0_ps_clk      ),
    .FIXED_IO_ps_porb          (FIXED_IO_0_ps_porb     ),
    .DDR_ck_p                  (DDR_0_ck_p             ),
    .DDR_ck_n                  (DDR_0_ck_n             ),
    .DDR_cke                   (DDR_0_cke              ),
    .DDR_cs_n                  (DDR_0_cs_n             ),
    .DDR_ras_n                 (DDR_0_ras_n            ),
    .DDR_cas_n                 (DDR_0_cas_n            ),
    .DDR_we_n                  (DDR_0_we_n             ),
    .DDR_ba                    (DDR_0_ba               ),
    .DDR_addr                  (DDR_0_addr             ),
    .DDR_odt                   (DDR_0_odt              ),
    .DDR_reset_n               (DDR_0_reset_n          ),
    .DDR_dq                    (DDR_0_dq               ),
    .DDR_dm                    (DDR_0_dm               ),
    .DDR_dqs_p                 (DDR_0_dqs_p            ),
    .DDR_dqs_n                 (DDR_0_dqs_n            ),
    .FIXED_IO_ddr_vrn          (FIXED_IO_0_ddr_vrn     ),
    .FIXED_IO_ddr_vrp          (FIXED_IO_0_ddr_vrp     ),
      
    .FCLK_RESET0_N             (FCLK_RESET0_N          ),
      
 //   .PJTAG_TCK                 (PJTAG_TCK              ),
 //   .PJTAG_TMS                 (PJTAG_TMS              ),
 //   .PJTAG_TDI                 (PJTAG_TDI              ),
 //   .PJTAG_TDO                 (PJTAG_TDO              ), 
            
    .ps_clk_out                (ps_clk_out             ),
      



    .test_irq                  (test_irq                 ),
    .customop_irq              (customop_irq             ),
    .ai_irq                    (ai_irq                   ),
	
    .gp0_ar_cnt                (gp0_ar_cnt               ),
    .gp0_r_cnt                 (gp0_r_cnt                ),
    .gp0_aw_cnt                (gp0_aw_cnt               ),   
    .gp0_w_cnt                 (gp0_w_cnt                ),
    .gp0_b_cnt                 (gp0_b_cnt                ),

    .gp1_ar_cnt                (gp1_ar_cnt               ),
    .gp1_r_cnt                 (gp1_r_cnt                ),
    .gp1_aw_cnt                (gp1_aw_cnt               ),
    .gp1_w_cnt                 (gp1_w_cnt                ),  
    .gp1_b_cnt                 (gp1_b_cnt                )          
    );

assign TWO_PHY_RSTN = locked ;

endmodule
