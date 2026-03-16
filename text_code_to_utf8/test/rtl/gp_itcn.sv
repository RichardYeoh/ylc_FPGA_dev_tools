//==============================================================================
// Orgnization   : Shanghai Fudan Microelectronics Co., Ltd. Confidential
// File Name     : gp_itcn.v
// Author        : wangyinglin
// Project       : 
// Create Date   : 2023.06.28
// Description   :
//------------------------------------------------------------------------------
// Modification History :
// Rev     Date         Who          Description
//==============================================================================

module gp_itcn #(parameter GP_BASE=32'h40000000)(
    mna_gp_ww_itf.slave     s0_gp      ,
    mna_gp_ww_itf.slave     s1_gp      ,
    mna_gp_ww_itf.master    m_gp       ,      

    input                   gpx_clk    ,
    input                   gpx_rst
);

  wire  [31 : 0]  gp_base ;

  assign gp_base = GP_BASE;
  //wr
    reg  [   3 : 0]   ack_wid          ;

    always@(*)begin
        if(s0_gp.awwvalid)
            ack_wid <= 4'h0;
        else if(s1_gp.awwvalid)
            ack_wid <= 4'h1;         
        else
            ack_wid <= 4'hF;
    end

    assign m_gp.awwvalid = (ack_wid!=4'hF);

    assign s0_gp.awwready = (ack_wid==4'd0) && m_gp.awwready ;
    assign s1_gp.awwready = (ack_wid==4'd1) && m_gp.awwready ;

    always@(*) begin
        case(ack_wid)
            4'd0   : m_gp.awwaddr <= s0_gp.awwaddr ;
            4'd1   : m_gp.awwaddr <= {gp_base[31:20],s1_gp.awwaddr[19:0]} ;
            default: m_gp.awwaddr <= 0;
        endcase
    end

    always@(*) begin
        case(ack_wid)
            4'd0   : m_gp.awwdata <= s0_gp.awwdata ;
            4'd1   : m_gp.awwdata <= s1_gp.awwdata ;
            default: m_gp.awwdata <= 0;
        endcase
    end

  //rd
    wire  [  2 : 0]   ack_arid          ;

    wire  [  2 : 0]   idfifo_din        ;
    wire  [  2 : 0]   idfifo_dout       ;
    wire              idfifo_wr         ;
    wire              idfifo_rd         ;
    wire              idfifo_full       ;
	wire              idfifo_pfull      ;
    wire              idfifo_empty      ;

    wire              arready           ;

    assign ack_arid   = s0_gp.arvalid ? 3'd0 :
                       (s1_gp.arvalid ? 3'd1 : 3'd7);
                       
    assign m_gp.arvalid  = (~idfifo_pfull) && (s0_gp.arvalid|s1_gp.arvalid);
    assign arready       = (~idfifo_pfull) && m_gp.arready;

    assign s0_gp.arready = (ack_arid==3'd0) && arready ;
    assign s1_gp.arready = (ack_arid==3'd1) && arready ;
 
    always@(*) begin
        case(ack_arid)
            3'd0   : m_gp.araddr <= s0_gp.araddr;
            3'd1   : m_gp.araddr <= {gp_base[31:20],s1_gp.araddr[19:0]};
            default: m_gp.araddr <= 0;
        endcase
    end

    assign s0_gp.rdata  = m_gp.rdata      ;
    assign s1_gp.rdata  = m_gp.rdata      ;

    assign s0_gp.rvalid = ((idfifo_dout[2:0]==3'd0) & ~idfifo_empty)  ? m_gp.rvalid :  1'b0 ;
    assign s1_gp.rvalid = ((idfifo_dout[2:0]==3'd1) & ~idfifo_empty)  ? m_gp.rvalid :  1'b0 ;

    always@(*) begin
        case(idfifo_dout[2:0])
            3'd0   : m_gp.rready <= s0_gp.rready & ~idfifo_empty;
            3'd1   : m_gp.rready <= s1_gp.rready & ~idfifo_empty;
            default: m_gp.rready <= 0;
        endcase
    end

    assign idfifo_din = ack_arid;
    assign idfifo_wr  = m_gp.arvalid  & m_gp.arready  ;
    assign idfifo_rd  = m_gp.rvalid & m_gp.rready;

    mna_idfifo mna_idfifo_u0(
        .clk       (gpx_clk         ),
        .srst      (gpx_rst         ),
        .din       (idfifo_din      ),
        .wr_en     (idfifo_wr       ),
        .rd_en     (idfifo_rd       ),
        .dout      (idfifo_dout     ),
        .prog_full (idfifo_pfull    ),
        .full      (idfifo_full     ),
        .empty     (idfifo_empty    )
    );  
endmodule
