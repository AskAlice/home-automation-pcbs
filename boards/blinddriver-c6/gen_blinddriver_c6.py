#!/usr/bin/env python3
"""blinddriver-c6 generator -- thin wrapper over boards/wave2/wave2gen.py."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "wave2"))
import wave2gen
if __name__ == "__main__":
    wave2gen.build("blinddriver-c6")
