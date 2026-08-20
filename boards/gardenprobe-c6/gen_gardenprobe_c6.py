#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "wave2"))
import wave2gen
if __name__ == "__main__":
    wave2gen.build("gardenprobe-c6")
