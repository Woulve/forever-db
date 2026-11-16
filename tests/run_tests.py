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
    shutil.copy(os.path.join(HERE, "rec2.lua"), col)
    with open(os.path.join(out, "Test_DB.toc"), "w") as f:
        f.write("## Interface: 16001\n## Version: 0\n\nold.lua\n")
    run("tools/import_base.py", dump, os.path.join(tmp, "base.json"))
    run("tools/build.py", "--base", os.path.join(tmp, "base.json"), "--collected", col, "--out", os.path.join(tmp, "forever.json"))
    spec = json.load(open(os.path.join(ROOT, "slices", "forever.json")))
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
    check("Questicus objective spots (near ones merged)", db["qsp"]["50001"]["1429"] == [400, 500, 700, 700])
    check("Questicus objective sources (seen 2+ times only)", db["qsrc"]["50001"] == ["o645516"])
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import build as _b
    t = {"qx": {1: [0, 0, None, None, None, None, 3], 2: [0, 0, None, None, None, None, 3], 3: [0], 4: [0, 0, [9], None, None, None, 5], 5: [0, 0, [7]]}}
    check("chain prerequisites from 'next' links (only where none exist)",
          _b.chain_prereqs(t) == 1 and t["qx"][3][2] == [1, 2] and t["qx"][5][2] == [7])
    check("fixes.json applied (Old Rot-Chum spot + note, extra quest giver)",
          db["spm"]["c257001"]["2548"] == [771, 728] and "murloc hut" in db["note"]["c257001"]
          and "c259961" in db["qg"]["95120"])
    toc = open(os.path.join(out, "Test_DB.toc")).read()
    check("toc lists data file", "ForeverDB.lua" in toc and "old.lua" not in toc)
    lua = open(os.path.join(out, "ForeverDB.lua")).read()
    check("lua written", "ForeverDB = ForeverDB or {}" in lua and ";(function()" in lua)
    exe = shutil.which("lua5.1") or shutil.which("lua") or shutil.which("texlua")
    if exe:
        chk = os.path.join(tmp, "check.lua")
        with open(chk, "w") as f:
            f.write('dofile([[%s]]) assert(ForeverDB.drop[5523][1]) print("lua loads")' % os.path.join(out, "ForeverDB.lua"))
        r = subprocess.run([exe, chk], capture_output=True, text=True)
        if r.returncode:
            print(r.stdout, r.stderr)
        check("lua file loads", r.returncode == 0)

    # ---- VMaNGOS: final-patch rows only, several creatures per spawn point
    vdump = os.path.join(tmp, "vdump"); os.makedirs(vdump)
    shutil.copy(os.path.join(HERE, "vm_mini.sql"), vdump)
    run("tools/import_base.py", vdump, os.path.join(tmp, "src-vmangos.json"))
    vm = json.load(open(os.path.join(tmp, "src-vmangos.json")))
    check("vmangos newest patch row", vm["npc"]["300"][0] == "New Name" and vm["npc"]["300"][2] == 3)
    check("vmangos drop valid in 1.12 kept", [300, 5000] in vm["drop"].get("9000", []))
    check("vmangos drop removed before 1.12 skipped", "9001" not in vm["drop"])
    check("vmangos spawn shared by id2", "c301" in vm["spw"] and "c300" in vm["spw"])
    check("vmangos spawn ended before 1.12 skipped", vm["spw"]["c301"] == [[0, 100, 201]])

    if exe:
        fx = os.path.join(HERE, "fixtures")
        conv = os.path.join(fx, "questiedb", "data", "Forever", "conversion.json")
        qj, pj = os.path.join(tmp, "questie.json"), os.path.join(tmp, "pfquest.json")
        subprocess.run([exe, "tools/lua/export.lua", "questie", os.path.join(fx, "questiedb"), "Forever", qj], check=True, cwd=ROOT)
        subprocess.run([exe, "tools/lua/export.lua", "pfquest", os.path.join(fx, "pfquest"), pj], check=True, cwd=ROOT)
        dng = os.path.join(fx, "questiedb", "support", "Forever", "Zones", "dungeons.lua")
        run("tools/import_addons.py", "questie", qj, os.path.join(tmp, "src-questie.json"), "--conversion", conv, "--dungeons", dng)
        run("tools/import_addons.py", "pfquest", pj, os.path.join(tmp, "src-pfquest.json"), "--zones", qj, "--conversion", conv)
        qs = json.load(open(os.path.join(tmp, "src-questie.json")))
        pf = json.load(open(os.path.join(tmp, "src-pfquest.json")))
        check("questie correction adds a Forever-only npc", qs["npc"].get("99999", [None])[0] == "Skyborne Scout")
        check("questie _add operation", "c100" in qs["qg"].get("50002", []))
        check("questie replacement", qs["npc"]["100"][2] == 12)
        check("questie quest details (qx) for every quest", set(qs["qx"]) == set(qs["quest"]))
        check("dungeon entrances (dng) incl. alternative area ids",
              qs["dng"].get("1581", [None])[0] == "The Deadmines" and qs["dng"].get("10029", [None])[0] == "The Deadmines"
              and qs["dng"]["717"][2][1:] == [524, 700])
        check("questie authored fix", qs["npc"]["101"][0] == "Kobold Tunneler")
        check("questie dynamic (per character) fixes skipped", qs["npc"]["101"][0] != "SHOULD NOT APPLY")
        check("questie spawn on Forever map", qs["spz"]["c99999"] == {"1429": [255, 402]})
        check("questie drop without rate", qs["drop"]["5523"] == [[100, 0]])
        check("pfquest rate per 10000", [100, 3000] in pf["drop"]["5523"])
        check("pfquest Classic map moved onto Forever map", pf["spz"]["c100"] == {"1412": [300, 400]})
        check("pfquest translations", pf["loc"]["deDE"]["npc"]["100"] == "Murlocräuber")
        # ---- merge: Forever source wins, vote for the rest, union of relations, median rates
        base_src = os.path.join(tmp, "base.json")
        run("tools/merge.py", "--out", os.path.join(tmp, "merged.json"), "--report", os.path.join(tmp, "report.json"),
            "questie=" + os.path.join(tmp, "src-questie.json"), "vmangos=" + os.path.join(tmp, "src-vmangos.json"),
            "cmangos=" + base_src, "pfquest=" + os.path.join(tmp, "src-pfquest.json"))
        m = json.load(open(os.path.join(tmp, "merged.json")))
        rep = json.load(open(os.path.join(tmp, "report.json")))
        check("merge keeps entries every source has", all(k in m["npc"] for k in ("100", "300", "99999", "777") if k != "777" or "777" in json.load(open(base_src))["npc"]))
        check("merge: Forever level wins", m["npc"]["100"][2] == 12)
        check("merge: Forever-only npc kept", m["npc"]["99999"][0] == "Skyborne Scout")
        check("merge: drop rate from sources with a rate", next(c for s, c in m["drop"]["5523"] if s == 100) > 0)
        check("merge: drop only pfQuest knows", any(s == 101 for s, _ in m["drop"]["5523"]))
        check("merge: source mask", m["src"]["npc"]["100"] & 1 == 1)
        check("merge report", rep["forever_only"]["npc"] >= 1 and "npc.minLv" in rep["conflicts"])
        check("report markdown", os.path.exists(os.path.join(tmp, "report.md")))
    # ---- AllTheThings preprocessor (Forever build: classic tags on, later expansions off)
    sys.path.insert(0, os.path.join(ROOT, "tools", "att"))
    from preprocess import preprocess, evaluate
    check("att: #if FOREVER on, AFTER TBC off", evaluate("FOREVER") and not evaluate("AFTER TBC") and evaluate("BEFORE 7.3.0"))
    check("att: NOT ANYCLASSIC off", not evaluate("NOT ANYCLASSIC"))
    pp = preprocess("a\n-- #if AFTER WRATH\nb\n-- #else\nc\n-- #endif\nd").split("\n")
    check("att: preprocess keeps the active branch and line numbers", pp == ["a", "", "", "", "c", "", "d"])
    run("tools/import_att.py", os.path.join(HERE, "fixtures", "att.json"), os.path.join(tmp, "src-att.json"))
    at = json.load(open(os.path.join(tmp, "src-att.json")))
    check("att: quest giver + level + reward + drop", at["qg"]["794"] == ["c3145"] and at["quest"]["794"][2] == 5
          and at["rew"]["4921"] == [794] and at["drop"]["4859"] == [[3183, 0]] and at["spz"]["c3145"] == {"1411": [428, 690]})
    # ---- Forever client tables
    run("tools/import_client.py", os.path.join(HERE, "fixtures", "client"), os.path.join(tmp, "src-client.json"))
    cl = json.load(open(os.path.join(tmp, "src-client.json")))
    check("client: item row (name, quality, reqLevel, ilvl, class)", cl["item"]["5523"][:5] == ["Small Barnacled Clam", 1, 7, 10, 0])
    check("client: item without a search name keeps class/icon", cl["item"]["9000"][4] == 7 and cl["item"]["9000"][7] == 134000)
    check("client: flight master", cl["taxi"]["1"][0] == "Northshire Abbey" and cl["taxi"]["1"][1] == 0)
    if exe:
        lj, sj = os.path.join(tmp, "legacy.json"), os.path.join(tmp, "spf.json")
        subprocess.run([exe, "tools/lua/export.lua", "ns", lj, os.path.join(HERE, "fixtures", "extra", "legacy.lua")], check=True, cwd=ROOT)
        subprocess.run([exe, "tools/lua/export.lua", "ns", sj, os.path.join(HERE, "fixtures", "extra", "spf.lua")], check=True, cwd=ROOT)
        run("tools/import_extra.py", "legacy", lj, os.path.join(tmp, "src-legacy.json"))
        run("tools/import_extra.py", "spf", sj, os.path.join(tmp, "src-spf.json"))
        lg = json.load(open(os.path.join(tmp, "src-legacy.json")))
        sp = json.load(open(os.path.join(tmp, "src-spf.json")))
        check("legacy: rewards + exploration outlines", lg["legacy"]["rewards"]["684"] is True and "1411" in lg["explore"])
        check("spf: travel tables", sp["spf"]["TaxiNodes"]["2"]["name"] == "Stormwind" and "Portals" in sp["spf"])
        # client item fields win the vote (Forever source first)
        run("tools/merge.py", "--out", os.path.join(tmp, "m2.json"), "client=" + os.path.join(tmp, "src-client.json"),
            "questie=" + os.path.join(tmp, "src-questie.json"), "att=" + os.path.join(tmp, "src-att.json"),
            "legacy=" + os.path.join(tmp, "src-legacy.json"), "spf=" + os.path.join(tmp, "src-spf.json"))
        m2 = json.load(open(os.path.join(tmp, "m2.json")))
        check("merge: client item row wins and is 12 columns", m2["item"]["5523"][2] == 7 and len(m2["item"]["5523"]) == 12)
        check("merge: pass-through tables", "1" in m2["taxi"] and "rewards" in m2["legacy"] and "TaxiNodes" in m2["spf"])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
