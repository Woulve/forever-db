"""End-to-end check of the pipeline on the tiny sample dump + sample recording."""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def run(*a):
    subprocess.run([sys.executable, *a], check=True, cwd=ROOT)


def main():
    tmp = tempfile.mkdtemp()
    dump, col, out = os.path.join(tmp, "dump"), os.path.join(tmp, "collected"), os.path.join(tmp, "addon")
    os.makedirs(dump); os.makedirs(col); os.makedirs(out)
    shutil.copy(os.path.join(HERE, "mini.sql"), dump)
    shutil.copy(os.path.join(HERE, "rec1.lua"), col)
    with open(os.path.join(out, "Test_DB.toc"), "w") as f:
        f.write("## Interface: 16001\n## Version: 0\n\nold.lua\n")
    run("tools/import_base.py", dump, os.path.join(tmp, "base.json"))
    run("tools/build.py", "--base", os.path.join(tmp, "base.json"), "--collected", col, "--out", os.path.join(tmp, "forever.json"))
    spec = json.load(open(os.path.join(ROOT, "slices", "commandcenter.json")))
    spec["toc"] = "Test_DB.toc"
    sp = os.path.join(tmp, "spec.json"); json.dump(spec, open(sp, "w"))
    run("tools/slice.py", sp, os.path.join(tmp, "forever.json"), out)
    db = json.load(open(os.path.join(tmp, "forever.json")))
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + name)
        ok = ok and cond
    check("forever rate replaces base after 20 loots", [100, 2000] in db["drop"]["5523"])
    check("forever-only creature drop added", [777, 7500] in db["drop"]["5523"])
    check("group equal share", db["drop"]["7000"] == [[101, 2500]])
    check("reference chance multiplied", db["drop"]["8001"] == [[101, 500]])
    check("vendor template", 200 in db["vend"]["5523"])
    check("recorded quest reward", 50001 in db["rew"]["5523"])
    check("renamed npc", db["npc"]["100"][0] == "Murloc Raider (Forever)")
    check("map spots", db["spm"]["c777"]["1429"] == [500, 600])
    toc = open(os.path.join(out, "Test_DB.toc")).read()
    check("toc lists data file", "ForeverDB.lua" in toc and "old.lua" not in toc)
    lua = open(os.path.join(out, "ForeverDB.lua")).read()
    check("lua written", "CC_ForeverDB" in lua and ";(function()" in lua)
    if shutil.which("texlua") or shutil.which("lua") or shutil.which("lua5.1"):
        exe = shutil.which("lua5.1") or shutil.which("lua") or shutil.which("texlua")
        chk = os.path.join(tmp, "check.lua")
        with open(chk, "w") as f:
            f.write('dofile([[%s]]) assert(CC_ForeverDB.drop[5523][1]) print("lua loads")' % os.path.join(out, "ForeverDB.lua"))
        r = subprocess.run([exe, chk], capture_output=True, text=True)
        if r.returncode:
            print(r.stdout, r.stderr)
        check("lua file loads", r.returncode == 0)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
