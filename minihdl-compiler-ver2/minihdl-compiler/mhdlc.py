#!/usr/bin/env python3
"""
mhdlc -- the MiniHDL compiler.

Usage:
    python mhdlc.py examples/full_adder.hdl --emit all -O2 --verify
"""

import sys
from minihdl.driver import main

if __name__ == "__main__":
    sys.exit(main())
