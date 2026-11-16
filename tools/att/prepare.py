"""Prepare AllTheThings' Lua database sources for tools/att/run.lua: preprocess every file of
.contrib/.db/shared (with .main.lua first) and .contrib/.db/forever into <work>, in the
parser's load order, and write <work>/order.txt.

  python tools/att/prepare.py <AllTheThings>/.contrib/.db work/att
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preprocess import preprocess  # noqa: E402


def lua_files(base):
    found = []
    for d, ds, fs in os.walk(base):
        ds.sort(key=str.lower)
        found += [os.path.join(d, f) for f in sorted(fs, key=str.lower) if f.lower().endswith(".lua")]
    return found


def main():
    root, work = sys.argv[1], sys.argv[2]
    shared = lua_files(os.path.join(root, "shared"))
    shared.sort(key=lambda p: os.path.basename(p) != ".main.lua")      # stable: .main.lua first
    forever = [p for p in lua_files(os.path.join(root, "forever")) if os.sep + ".wago" + os.sep not in p]
    order = []
    for p in shared + forever:
        dst = os.path.join(work, os.path.relpath(p, root))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(p, encoding="utf-8-sig") as f, open(dst, "w", encoding="utf-8") as g:
            g.write(preprocess(f.read()))
        order.append(dst)
    with open(os.path.join(work, "order.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(order) + "\n")
    print("att: %d shared + %d forever files" % (len(shared), len(forever)))


if __name__ == "__main__":
    main()
