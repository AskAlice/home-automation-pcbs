#!/usr/bin/env python3
"""threadnode-h2 generator -- thin wrapper over boards/wave2/wave2gen.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "wave2"))
import wave2gen

if __name__ == "__main__":
    wave2gen.build("threadnode-h2")
