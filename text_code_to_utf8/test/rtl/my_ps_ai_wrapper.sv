//Copyright fmsh, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2020.2 (lin64)
//Design      : ps_ai_wrapper
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

module my_ps_ai_wrapper (
    inout [14:0] DDR_addr,
    inout [2:0]  DDR_ba,
    inout        DDR_cas_n,
    inout        DDR_ck_n,
    inout        DDR_ck_p,
    inout        DDR_cke,
    inout        DDR_cs_n,
    inout [3:0]  DDR_dm,
    inout [31:0] DDR_dq,
    inout [3:0]  DDR_dqs_n,
    inout [3:0]  DDR_dqs_p,
    inout        DDR_odt,
    inout        DDR_ras_n,
    inout        DDR_reset_n,
    inout        DDR_we_n,
    inout        FIXED_IO_ddr_vrn,
    inout        FIXED_IO_ddr_vrp,
    inout [53:0] FIXED_IO_mio,
    inout        FIXED_IO_ps_clk,
    inout        FIXED_IO_ps_porb,
    inout        FIXED_IO_ps_srstb,
  
    output       FCLK_RESET0_N,
    
    input        hp_axi_aclk,
    output       ps_clk_out,
	
	
	// input        UART_0_0_rxd ,
	// output		 UART_0_0_txd ,
	// input    	 UART_1_0_rxd ,
	// output	 	 UART_1_0_txd ,
	
	output MDIO_PHY_0_mdc,
	inout MDIO_PHY_0_mdio_io,
	input PJTAG_0_tck,
	input PJTAG_0_tdi,
	output PJTAG_0_tdo,
	input PJTAG_0_tms,
	input [3:0]RGMII_0_rd,
	input RGMII_0_rx_ctl,
	input RGMII_0_rxc,
	output [3:0]RGMII_0_td,
	output RGMII_0_tx_ctl,
	output RGMII_0_txc,	

  output [15:0]DDR3_0_addr,
  output [2:0]DDR3_0_ba,
  output DDR3_0_cas_n,
  output [0:0]DDR3_0_ck_n,
  output [0:0]DDR3_0_ck_p,
  output [0:0]DDR3_0_cke,
  output [0:0]DDR3_0_cs_n,
  output [3:0]DDR3_0_dm,
  inout [31:0]DDR3_0_dq,
  inout [3:0]DDR3_0_dqs_n,
  inout [3:0]DDR3_0_dqs_p,
  output [0:0]DDR3_0_odt,
  output DDR3_0_ras_n,
  output DDR3_0_reset_n,
  output DDR3_0_we_n,
  output ddr_mmcm_locked,
  output init_calib_complete,
  input [3:0]pcie_mgt_0_rxn,
  input [3:0]pcie_mgt_0_rxp,
  output [3:0]pcie_mgt_0_txn,
  output [3:0]pcie_mgt_0_txp,
  input [0:0]pcie_ref_clk_clk_n,
  input [0:0]pcie_ref_clk_clk_p,
  input sys_clk_i_0,
  output ui_clk,
  output [0:0]mig_ui_rst_n,
  output user_lnk_up_0,
	
  /////////////////////////////sar_proc here/////////////////////////////////
  
  
        output [31:0]M_AXIS_S2MM_STS_head_tdata,
        output [3:0]M_AXIS_S2MM_STS_head_tkeep,
        output M_AXIS_S2MM_STS_head_tlast     ,
        input M_AXIS_S2MM_STS_head_tready     ,
        output M_AXIS_S2MM_STS_head_tvalid    ,
                                              
        input [71:0]S_AXIS_S2MM_CMD_head_tdata,
        output S_AXIS_S2MM_CMD_head_tready    ,
        input S_AXIS_S2MM_CMD_head_tvalid     ,
        input [31:0]S_AXIS_S2MM_head_tdata    ,
        input [3:0]S_AXIS_S2MM_head_tkeep     ,
        input S_AXIS_S2MM_head_tlast          ,
        output S_AXIS_S2MM_head_tready        ,
        input S_AXIS_S2MM_head_tvalid         ,
        
        output [31:0]M_AXIS_S2MM_STS_img_tdata,
        output [3:0]M_AXIS_S2MM_STS_img_tkeep,
        output M_AXIS_S2MM_STS_img_tlast     ,
        input M_AXIS_S2MM_STS_img_tready     ,
        output M_AXIS_S2MM_STS_img_tvalid    ,
                                              
        input [71:0]S_AXIS_S2MM_CMD_img_tdata,
        output S_AXIS_S2MM_CMD_img_tready    ,
        input S_AXIS_S2MM_CMD_img_tvalid     ,
        input [31:0]S_AXIS_S2MM_img_tdata    ,
        input [3:0]S_AXIS_S2MM_img_tkeep     ,
        input S_AXIS_S2MM_img_tlast          ,
        output S_AXIS_S2MM_img_tready        ,
        input S_AXIS_S2MM_img_tvalid         ,
        
  
        input [31:0]sar_info_buf_addr         ,
        input sar_info_buf_clk                ,
        input [31:0]sar_info_buf_din          ,
        output [31:0]sar_info_buf_dout        ,
        input sar_info_buf_en                 ,
        input sar_info_buf_rst                ,
        input [3:0]sar_info_buf_we            ,
  /////////////////////////////sar_proc end/////////////////////////////////
  
    input                 test_irq         ,
    input                 customop_irq     ,    
    input                 ai_irq           ,

	input 				M02_ACLK_0			,
	input 				M02_ARESETN_0       ,
	output	 [31:0]		M02_AXI_0_araddr    ,
	output	 [1:0]		M02_AXI_0_arburst   ,
	output	 [3:0]		M02_AXI_0_arcache   ,
	output	 [11:0]		M02_AXI_0_arid      ,
	output	 [7:0]		M02_AXI_0_arlen     ,
	output	 [0:0]		M02_AXI_0_arlock    ,
	output	 [2:0]		M02_AXI_0_arprot    ,
	output	 [3:0]		M02_AXI_0_arqos     ,
	input 				M02_AXI_0_arready   ,
	output	 [3:0]		M02_AXI_0_arregion  ,
	output	 [2:0]		M02_AXI_0_arsize    ,
	output	 			M02_AXI_0_arvalid   ,
	output	 [31:0]		M02_AXI_0_awaddr    ,
	output	 [1:0]		M02_AXI_0_awburst   ,
	output	 [3:0]		M02_AXI_0_awcache   ,
	output	 [11:0]		M02_AXI_0_awid      ,
	output	 [7:0]		M02_AXI_0_awlen     ,
	output	 [0:0]		M02_AXI_0_awlock    ,
	output	 [2:0]		M02_AXI_0_awprot    ,
	output	 [3:0]		M02_AXI_0_awqos     ,
	input 				M02_AXI_0_awready   ,
	output	 [3:0]		M02_AXI_0_awregion  ,
	output	 [2:0]		M02_AXI_0_awsize    ,
	output	 			M02_AXI_0_awvalid   ,
	input 	[11:0]		M02_AXI_0_bid       ,
	output	 			M02_AXI_0_bready    ,
	input 	[1:0]		M02_AXI_0_bresp     ,
	input 				M02_AXI_0_bvalid    ,
	input 	[31:0]		M02_AXI_0_rdata     ,
	input 	[11:0]		M02_AXI_0_rid       ,
	input 				M02_AXI_0_rlast     ,
	output	 			M02_AXI_0_rready    ,
	input 	[1:0]		M02_AXI_0_rresp     ,
	input 				M02_AXI_0_rvalid    ,
	output	 [31:0]		M02_AXI_0_wdata     ,
	output	 			M02_AXI_0_wlast     ,
	input 				M02_AXI_0_wready    ,
	output	 [3:0]		M02_AXI_0_wstrb     ,
	output	 			M02_AXI_0_wvalid    ,

	// output 	[15:0]			BRAM_PORTA_0_addr	,
	// output 					BRAM_PORTA_0_clk    ,
	// output	[31:0]			BRAM_PORTA_0_din    ,
	// input	[31:0]			BRAM_PORTA_0_dout   ,
	// output 					BRAM_PORTA_0_en     ,
	// output 					BRAM_PORTA_0_rst    ,
	// output 	[3:0]			BRAM_PORTA_0_we     ,


    output   [ 31 : 0]    gp0_ar_cnt       ,        
    output   [ 31 : 0]    gp0_r_cnt        ,        
    output   [ 31 : 0]    gp0_aw_cnt       ,           
    output   [ 31 : 0]    gp0_w_cnt        ,        
    output   [ 31 : 0]    gp0_b_cnt        ,        

    output   [ 31 : 0]    gp1_ar_cnt       ,        
    output   [ 31 : 0]    gp1_r_cnt        ,        
    output   [ 31 : 0]    gp1_aw_cnt       ,        
    output   [ 31 : 0]    gp1_w_cnt        ,          
    output   [ 31 : 0]    gp1_b_cnt         
    );
              
  wire gp_axi_aclk;
  wire clk_300m;
  wire pll_lock;
  wire FCLK_CLK0;
   
  
  assign ps_clk_out = gp_axi_aclk;

  IOBUF MDIO_PHY_0_mdio_iobuf
       (.I(MDIO_PHY_0_mdio_o),
        .IO(MDIO_PHY_0_mdio_io),
        .O(MDIO_PHY_0_mdio_i),
        .T(MDIO_PHY_0_mdio_t));

ps_ai ps_ai_i(

        .RGMII_0_rd(RGMII_0_rd),
        .RGMII_0_rx_ctl(RGMII_0_rx_ctl),
        .RGMII_0_rxc(RGMII_0_rxc),
        .RGMII_0_td(RGMII_0_td),
        .RGMII_0_tx_ctl(RGMII_0_tx_ctl),
        .RGMII_0_txc(RGMII_0_txc),

        .MDIO_PHY_0_mdc(MDIO_PHY_0_mdc),
        .MDIO_PHY_0_mdio_i(MDIO_PHY_0_mdio_i),
        .MDIO_PHY_0_mdio_o(MDIO_PHY_0_mdio_o),
        .MDIO_PHY_0_mdio_t(MDIO_PHY_0_mdio_t),

        .DDR3_0_addr(DDR3_0_addr),
        .DDR3_0_ba(DDR3_0_ba),
        .DDR3_0_cas_n(DDR3_0_cas_n),
        .DDR3_0_ck_n(DDR3_0_ck_n),
        .DDR3_0_ck_p(DDR3_0_ck_p),
        .DDR3_0_cke(DDR3_0_cke),
        .DDR3_0_cs_n(DDR3_0_cs_n),
        .DDR3_0_dm(DDR3_0_dm),
        .DDR3_0_dq(DDR3_0_dq),
        .DDR3_0_dqs_n(DDR3_0_dqs_n),
        .DDR3_0_dqs_p(DDR3_0_dqs_p),
        .DDR3_0_odt(DDR3_0_odt),
        .DDR3_0_ras_n(DDR3_0_ras_n),
        .DDR3_0_reset_n(DDR3_0_reset_n),
        .DDR3_0_we_n(DDR3_0_we_n),
        .ddr_mmcm_locked(ddr_mmcm_locked),
        .init_calib_complete(init_calib_complete),
        .pcie_mgt_0_rxn(pcie_mgt_0_rxn),
        .pcie_mgt_0_rxp(pcie_mgt_0_rxp),
        .pcie_mgt_0_txn(pcie_mgt_0_txn),
        .pcie_mgt_0_txp(pcie_mgt_0_txp),
        .pcie_ref_clk_clk_n(pcie_ref_clk_clk_n),
        .pcie_ref_clk_clk_p(pcie_ref_clk_clk_p),
        .sys_clk_i_0(sys_clk_i_0),
        .ui_clk(ui_clk),
        .mig_ui_rst_n(mig_ui_rst_n),        //  output [0:0]mig_ui_rst_n;
        .user_lnk_up_0(user_lnk_up_0),


  .DDR_0_addr                         (DDR_addr                           ),
  .DDR_0_ba                           (DDR_ba                             ),
  .DDR_0_cas_n                        (DDR_cas_n                          ),
  .DDR_0_ck_n                         (DDR_ck_n                           ),
  .DDR_0_ck_p                         (DDR_ck_p                           ),
  .DDR_0_cke                          (DDR_cke                            ),
  .DDR_0_cs_n                         (DDR_cs_n                           ),
  .DDR_0_dm                           (DDR_dm                             ),
  .DDR_0_dq                           (DDR_dq                             ),
  .DDR_0_dqs_n                        (DDR_dqs_n                          ),
  .DDR_0_dqs_p                        (DDR_dqs_p                          ),
  .DDR_0_odt                          (DDR_odt                            ),
  .DDR_0_ras_n                        (DDR_ras_n                          ),
  .DDR_0_reset_n                      (DDR_reset_n                        ),
  .DDR_0_we_n                         (DDR_we_n                           ),
  .FCLK_CLK0_0                        (FCLK_CLK0                          ),
  .FCLK_RESET0_N_0                    (FCLK_RESET0_N                      ),
  .FIXED_IO_0_ddr_vrn                 (FIXED_IO_ddr_vrn                   ),
  .FIXED_IO_0_ddr_vrp                 (FIXED_IO_ddr_vrp                   ),
  .FIXED_IO_0_mio                     (FIXED_IO_mio                       ),
  .FIXED_IO_0_ps_clk                  (FIXED_IO_ps_clk                    ),
  .FIXED_IO_0_ps_porb                 (FIXED_IO_ps_porb                   ),
  .FIXED_IO_0_ps_srstb                (FIXED_IO_ps_srstb                  ),

  .PJTAG_0_tck                        (PJTAG_0_tck                        ),
  .PJTAG_0_tdi                        (PJTAG_0_tdi                        ),
  .PJTAG_0_tdo                        (PJTAG_0_tdo                        ),
  .PJTAG_0_tms                        (PJTAG_0_tms                        ),


 // .USBIND_0_0_port_indctl             (                                   ),
 // .USBIND_0_0_vbus_pwrfault           (                                   ),
 // .USBIND_0_0_vbus_pwrselect          (1'b0                               ),


  
  
  
    // .UART_0_0_rxd(UART_0_0_rxd),
    // .UART_0_0_txd(UART_0_0_txd),
    // .UART_1_0_rxd(UART_1_0_rxd),
    // .UART_1_0_txd(UART_1_0_txd),
  
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
  
  
  
  
  
  .AI_EXHS_0_pl_exhs                  (pl_exhs                            ),
  .AI_EXHS_0_pl_exhs_ack              (pl_exhs_ack                        ),
  .AI_EXHS_0_pl_exhs_vld              (pl_exhs_vld                        ),
  .AI_SCAN_0_pl_scan_en               (pl_scan_en                         ),
  .AI_SCAN_0_pl_scan_i                (pl_scan_i                          ),
  .AI_SCAN_0_pl_scan_mode_b           (pl_scan_mode_b                     ),
  .AI_SCAN_0_pl_scan_o                (pl_scan_o                          ),
  .AI_STATUS_0_pl_bist_done           (pl_bist_done                       ),
  .AI_STATUS_0_pl_bist_err            (pl_bist_err                        ),
  .AI_STATUS_0_pl_buyi_error          (pl_buyi_error                      ),
  .AI_STATUS_0_pl_clk_div_out         (pl_clk_div_out                     ),
  .AI_STATUS_0_pl_repair_done         (pl_repair_done                     ),
  .AI_STATUS_0_pl_repair_fail         (pl_repair_fail                     ),

  .test_irq                           (test_irq                           ),
  .customop_irq                       (customop_irq                       ),
  .ai_irq                             (ai_irq                             )

 
);

clk_wiz_0 clk_wiz_0_inst(

  .clk_out1(gp_axi_aclk),
  .reset(1'b0),
  .locked(pll_lock),
  .clk_in1(FCLK_CLK0)
  );

endmodule
