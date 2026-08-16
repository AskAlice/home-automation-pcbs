#!/usr/bin/env python3
"""Remove (model ...) blocks that are NOT direct children of their footprint,
then insert a single model as a direct child of each footprint that needs one."""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def match_paren(s, i):
    """index of ')' matching '(' at i"""
    d = 0
    in_str = False
    for j in range(i, len(s)):
        c = s[j]
        if c == '"':
            in_str = not in_str
        if in_str:
            continue
        if c == '(':
            d += 1
        elif c == ')':
            d -= 1
            if d == 0:
                return j
    return -1

def depth_at(s, i):
    d = 0; in_str = False
    for j in range(0, i):
        c = s[j]
        if c == '"':
            in_str = not in_str
        elif not in_str:
            if c == '(': d += 1
            elif c == ')': d -= 1
    return d

for pcb in sorted(glob.glob(os.path.join(ROOT, "boards", "*", "*.kicad_pcb"))):
    txt = open(pcb).read()
    board = os.path.basename(os.path.dirname(pcb))
    removed = inserted = 0
    # process each footprint independently, from last to first to keep offsets
    fp_iter = list(re.finditer(r'\(footprint\s+"([^"]+)"', txt))
    for m in reversed(fp_iter):
        fstart = m.start()
        fend = match_paren(txt, fstart)
        block = txt[fstart:fend + 1]
        # find model blocks inside this footprint block
        models = []
        for mm in re.finditer(r'\(model\s', block):
            mi = mm.start()
            # depth relative to footprint root: direct child = depth 1
            d = depth_at(block, mi)
            mend = match_paren(block, mi)
            models.append((mi, mend, d))
        if not models:
            continue
        # remove non-direct or duplicate models; keep at most one direct one
        keep = None
        direct = [x for x in models if x[2] == 1]
        if direct:
            keep = direct[0]
        newblock = block
        for (mi, mend, d) in reversed(models):
            if keep and mi == keep[0]:
                continue
            newblock = newblock[:mi] + newblock[mend + 1:]
            removed += 1
        if keep is None and models:
            # re-insert first model as direct child before footprint close
            mi0, mend0, _ = models[0]
            modeltxt = block[mi0:mend0 + 1]
            newblock = newblock[:-1] + "\n    " + modeltxt.strip() + "\n  )"
            inserted += 1
        txt = txt[:fstart] + newblock + txt[fend + 1:]
    open(pcb, "w").write(txt)
    print(board, "removed", removed, "reinserted", inserted)
