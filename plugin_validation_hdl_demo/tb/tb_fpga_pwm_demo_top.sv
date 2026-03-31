`timescale 1ns/1ps

module tb_fpga_pwm_demo_top;

    reg         clk;
    reg         rst_n;
    reg         cfg_wr_en;
    reg  [3:0]  cfg_addr;
    reg  [31:0] cfg_wr_data;
    wire        pwm_out;
    wire        heartbeat_led;
    wire [11:0] debug_phase;

    integer high_count;
    integer sample_count;
    integer heartbeat_toggle_count;
    reg previous_heartbeat;

    fpga_pwm_demo_top u_dut (
        .clk(clk),
        .rst_n(rst_n),
        .cfg_wr_en(cfg_wr_en),
        .cfg_addr(cfg_addr),
        .cfg_wr_data(cfg_wr_data),
        .pwm_out(pwm_out),
        .heartbeat_led(heartbeat_led),
        .debug_phase(debug_phase)
    );

    always #5 clk = ~clk;

    task automatic cfg_write;
        input [3:0] addr;
        input [31:0] data;
        begin
            @(negedge clk);
            cfg_addr <= addr;
            cfg_wr_data <= data;
            cfg_wr_en <= 1'b1;
            @(negedge clk);
            cfg_wr_en <= 1'b0;
            cfg_addr <= 4'h0;
            cfg_wr_data <= 32'h0;
        end
    endtask

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        cfg_wr_en = 1'b0;
        cfg_addr = 4'h0;
        cfg_wr_data = 32'h0;
        high_count = 0;
        sample_count = 0;
        heartbeat_toggle_count = 0;
        previous_heartbeat = 1'b0;

        repeat (5) @(negedge clk);
        rst_n = 1'b1;

        cfg_write(4'h1, 32'd2);
        cfg_write(4'h2, 32'd8);
        cfg_write(4'h3, 32'd3);
        cfg_write(4'h4, 32'd4);
        cfg_write(4'h0, 32'd1);

        repeat (80) begin
            @(posedge clk);
            if (u_dut.slow_tick) begin
                sample_count = sample_count + 1;
                if (pwm_out) begin
                    high_count = high_count + 1;
                end
                if (heartbeat_led != previous_heartbeat) begin
                    heartbeat_toggle_count = heartbeat_toggle_count + 1;
                    previous_heartbeat = heartbeat_led;
                end
            end
        end

        if (sample_count < 16) begin
            $fatal(1, "Not enough PWM samples were collected");
        end

        if (high_count < 12 || high_count > 18) begin
            $fatal(1, "PWM duty ratio is outside the expected range: %0d", high_count);
        end

        if (heartbeat_toggle_count < 2) begin
            $fatal(1, "Heartbeat LED did not toggle as expected");
        end

        $display(
            "TB_PASS sample_count=%0d high_count=%0d heartbeat_toggle_count=%0d final_phase=%0d",
            sample_count,
            high_count,
            heartbeat_toggle_count,
            debug_phase
        );
        $finish;
    end

endmodule
