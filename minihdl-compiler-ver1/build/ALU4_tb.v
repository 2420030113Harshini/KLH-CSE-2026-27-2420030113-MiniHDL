// Auto-generated self-checking testbench for ALU4
`timescale 1ns/1ps

module tb_ALU4;
    integer errors = 0;
    reg [3:0] a;
    reg [3:0] b;
    reg [1:0] op;
    wire [3:0] y;
    wire zero;
    wire eq;

    ALU4 dut (.a(a), .b(b), .op(op), .y(y), .zero(zero), .eq(eq));

    initial begin
        a = 4'd0;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd0) begin errors = errors + 1; $display("FAIL y: got %b want 4'd0", y); end
        if (zero !== 1'd1) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd1", zero); end
        if (eq !== 1'd1) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd1", eq); end
        a = 4'd1;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd1) begin errors = errors + 1; $display("FAIL y: got %b want 4'd1", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd2;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd2) begin errors = errors + 1; $display("FAIL y: got %b want 4'd2", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd3;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd3) begin errors = errors + 1; $display("FAIL y: got %b want 4'd3", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd4;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd4) begin errors = errors + 1; $display("FAIL y: got %b want 4'd4", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd5;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd5) begin errors = errors + 1; $display("FAIL y: got %b want 4'd5", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd6;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd6) begin errors = errors + 1; $display("FAIL y: got %b want 4'd6", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd7;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd7) begin errors = errors + 1; $display("FAIL y: got %b want 4'd7", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd8;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd8) begin errors = errors + 1; $display("FAIL y: got %b want 4'd8", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd9;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd9) begin errors = errors + 1; $display("FAIL y: got %b want 4'd9", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd10;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd10) begin errors = errors + 1; $display("FAIL y: got %b want 4'd10", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd11;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd11) begin errors = errors + 1; $display("FAIL y: got %b want 4'd11", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd12;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd12) begin errors = errors + 1; $display("FAIL y: got %b want 4'd12", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd13;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd13) begin errors = errors + 1; $display("FAIL y: got %b want 4'd13", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd14;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd14) begin errors = errors + 1; $display("FAIL y: got %b want 4'd14", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd15;
        b = 4'd0;
        op = 2'd0;
        #1;
        if (y !== 4'd15) begin errors = errors + 1; $display("FAIL y: got %b want 4'd15", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd0;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd1) begin errors = errors + 1; $display("FAIL y: got %b want 4'd1", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd1;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd2) begin errors = errors + 1; $display("FAIL y: got %b want 4'd2", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd1) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd1", eq); end
        a = 4'd2;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd3) begin errors = errors + 1; $display("FAIL y: got %b want 4'd3", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd3;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd4) begin errors = errors + 1; $display("FAIL y: got %b want 4'd4", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd4;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd5) begin errors = errors + 1; $display("FAIL y: got %b want 4'd5", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd5;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd6) begin errors = errors + 1; $display("FAIL y: got %b want 4'd6", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd6;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd7) begin errors = errors + 1; $display("FAIL y: got %b want 4'd7", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd7;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd8) begin errors = errors + 1; $display("FAIL y: got %b want 4'd8", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd8;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd9) begin errors = errors + 1; $display("FAIL y: got %b want 4'd9", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd9;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd10) begin errors = errors + 1; $display("FAIL y: got %b want 4'd10", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd10;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd11) begin errors = errors + 1; $display("FAIL y: got %b want 4'd11", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd11;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd12) begin errors = errors + 1; $display("FAIL y: got %b want 4'd12", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd12;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd13) begin errors = errors + 1; $display("FAIL y: got %b want 4'd13", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd13;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd14) begin errors = errors + 1; $display("FAIL y: got %b want 4'd14", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd14;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd15) begin errors = errors + 1; $display("FAIL y: got %b want 4'd15", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd15;
        b = 4'd1;
        op = 2'd0;
        #1;
        if (y !== 4'd0) begin errors = errors + 1; $display("FAIL y: got %b want 4'd0", y); end
        if (zero !== 1'd1) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd1", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd0;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd2) begin errors = errors + 1; $display("FAIL y: got %b want 4'd2", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd1;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd3) begin errors = errors + 1; $display("FAIL y: got %b want 4'd3", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd2;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd4) begin errors = errors + 1; $display("FAIL y: got %b want 4'd4", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd1) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd1", eq); end
        a = 4'd3;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd5) begin errors = errors + 1; $display("FAIL y: got %b want 4'd5", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd4;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd6) begin errors = errors + 1; $display("FAIL y: got %b want 4'd6", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd5;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd7) begin errors = errors + 1; $display("FAIL y: got %b want 4'd7", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd6;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd8) begin errors = errors + 1; $display("FAIL y: got %b want 4'd8", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd7;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd9) begin errors = errors + 1; $display("FAIL y: got %b want 4'd9", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd8;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd10) begin errors = errors + 1; $display("FAIL y: got %b want 4'd10", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd9;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd11) begin errors = errors + 1; $display("FAIL y: got %b want 4'd11", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd10;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd12) begin errors = errors + 1; $display("FAIL y: got %b want 4'd12", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd11;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd13) begin errors = errors + 1; $display("FAIL y: got %b want 4'd13", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd12;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd14) begin errors = errors + 1; $display("FAIL y: got %b want 4'd14", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd13;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd15) begin errors = errors + 1; $display("FAIL y: got %b want 4'd15", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd14;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd0) begin errors = errors + 1; $display("FAIL y: got %b want 4'd0", y); end
        if (zero !== 1'd1) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd1", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd15;
        b = 4'd2;
        op = 2'd0;
        #1;
        if (y !== 4'd1) begin errors = errors + 1; $display("FAIL y: got %b want 4'd1", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd0;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd3) begin errors = errors + 1; $display("FAIL y: got %b want 4'd3", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd1;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd4) begin errors = errors + 1; $display("FAIL y: got %b want 4'd4", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd2;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd5) begin errors = errors + 1; $display("FAIL y: got %b want 4'd5", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd3;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd6) begin errors = errors + 1; $display("FAIL y: got %b want 4'd6", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd1) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd1", eq); end
        a = 4'd4;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd7) begin errors = errors + 1; $display("FAIL y: got %b want 4'd7", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd5;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd8) begin errors = errors + 1; $display("FAIL y: got %b want 4'd8", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd6;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd9) begin errors = errors + 1; $display("FAIL y: got %b want 4'd9", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd7;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd10) begin errors = errors + 1; $display("FAIL y: got %b want 4'd10", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd8;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd11) begin errors = errors + 1; $display("FAIL y: got %b want 4'd11", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd9;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd12) begin errors = errors + 1; $display("FAIL y: got %b want 4'd12", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd10;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd13) begin errors = errors + 1; $display("FAIL y: got %b want 4'd13", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd11;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd14) begin errors = errors + 1; $display("FAIL y: got %b want 4'd14", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd12;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd15) begin errors = errors + 1; $display("FAIL y: got %b want 4'd15", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd13;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd0) begin errors = errors + 1; $display("FAIL y: got %b want 4'd0", y); end
        if (zero !== 1'd1) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd1", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd14;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd1) begin errors = errors + 1; $display("FAIL y: got %b want 4'd1", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        a = 4'd15;
        b = 4'd3;
        op = 2'd0;
        #1;
        if (y !== 4'd2) begin errors = errors + 1; $display("FAIL y: got %b want 4'd2", y); end
        if (zero !== 1'd0) begin errors = errors + 1; $display("FAIL zero: got %b want 1'd0", zero); end
        if (eq !== 1'd0) begin errors = errors + 1; $display("FAIL eq: got %b want 1'd0", eq); end
        if (errors == 0) $display("PASS: all vectors matched");
        else $display("%0d mismatches", errors);
        $finish;
    end
endmodule
