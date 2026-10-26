// Auto-generated self-checking testbench for FullAdder
`timescale 1ns/1ps

module tb_FullAdder;
    integer errors = 0;
    reg a;
    reg b;
    reg cin;
    wire sum;
    wire cout;

    FullAdder dut (.a(a), .b(b), .cin(cin), .sum(sum), .cout(cout));

    initial begin
        a = 1'd0;
        b = 1'd0;
        cin = 1'd0;
        #1;
        if (sum !== 1'd0) begin errors = errors + 1; $display("FAIL sum: got %b want 1'd0", sum); end
        if (cout !== 1'd0) begin errors = errors + 1; $display("FAIL cout: got %b want 1'd0", cout); end
        a = 1'd1;
        b = 1'd0;
        cin = 1'd0;
        #1;
        if (sum !== 1'd1) begin errors = errors + 1; $display("FAIL sum: got %b want 1'd1", sum); end
        if (cout !== 1'd0) begin errors = errors + 1; $display("FAIL cout: got %b want 1'd0", cout); end
        a = 1'd0;
        b = 1'd1;
        cin = 1'd0;
        #1;
        if (sum !== 1'd1) begin errors = errors + 1; $display("FAIL sum: got %b want 1'd1", sum); end
        if (cout !== 1'd0) begin errors = errors + 1; $display("FAIL cout: got %b want 1'd0", cout); end
        a = 1'd1;
        b = 1'd1;
        cin = 1'd0;
        #1;
        if (sum !== 1'd0) begin errors = errors + 1; $display("FAIL sum: got %b want 1'd0", sum); end
        if (cout !== 1'd1) begin errors = errors + 1; $display("FAIL cout: got %b want 1'd1", cout); end
        a = 1'd0;
        b = 1'd0;
        cin = 1'd1;
        #1;
        if (sum !== 1'd1) begin errors = errors + 1; $display("FAIL sum: got %b want 1'd1", sum); end
        if (cout !== 1'd0) begin errors = errors + 1; $display("FAIL cout: got %b want 1'd0", cout); end
        a = 1'd1;
        b = 1'd0;
        cin = 1'd1;
        #1;
        if (sum !== 1'd0) begin errors = errors + 1; $display("FAIL sum: got %b want 1'd0", sum); end
        if (cout !== 1'd1) begin errors = errors + 1; $display("FAIL cout: got %b want 1'd1", cout); end
        a = 1'd0;
        b = 1'd1;
        cin = 1'd1;
        #1;
        if (sum !== 1'd0) begin errors = errors + 1; $display("FAIL sum: got %b want 1'd0", sum); end
        if (cout !== 1'd1) begin errors = errors + 1; $display("FAIL cout: got %b want 1'd1", cout); end
        a = 1'd1;
        b = 1'd1;
        cin = 1'd1;
        #1;
        if (sum !== 1'd1) begin errors = errors + 1; $display("FAIL sum: got %b want 1'd1", sum); end
        if (cout !== 1'd1) begin errors = errors + 1; $display("FAIL cout: got %b want 1'd1", cout); end
        if (errors == 0) $display("PASS: all vectors matched");
        else $display("%0d mismatches", errors);
        $finish;
    end
endmodule
