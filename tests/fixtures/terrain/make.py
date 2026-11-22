"""A tiny continent for tests/run_tests.py: two ADT tiles of zone 1 with a 4 x 4 chunk sub-zone 2.
python make.py <out folder> -> <out>/files/<fileID>.bin and <out>/csv/*.csv"""
import sys
import struct, os, csv
os.chdir(sys.argv[1])
def chunk(tag, data): return tag[::-1].encode() + struct.pack("<I", len(data)) + data
os.makedirs("files", exist_ok=True); os.makedirs("csv", exist_ok=True)
main = bytearray(4096*8); maid = bytearray(4096*32)
for n, fid in ((0, 1001), (1, 1002)):          # tiles (row 0, col 0) and (row 0, col 1)
    struct.pack_into("<I", main, n*8, 1); struct.pack_into("<I", maid, n*32, fid)
open("files/900.bin","wb").write(chunk("MVER", struct.pack("<I",18)) + chunk("MAIN", bytes(main)) + chunk("MAID", bytes(maid)))
for fid, tx in ((1001, 0), (1002, 1)):
    out = chunk("MVER", struct.pack("<I",18))
    for iy in range(16):
        for ix in range(16):
            area = 2 if (tx == 0 and 4 <= ix < 8 and 4 <= iy < 8) else 1
            hdr = bytearray(0x80); struct.pack_into("<3I", hdr, 0, 0, ix, iy); struct.pack_into("<I", hdr, 0x34, area)
            out += chunk("MCNK", bytes(hdr))
    open("files/%d.bin" % fid, "wb").write(out + b"\0"*200)
def w(name, rows):
    with open("csv/%s.1.60.1.1.csv" % name, "w", newline="") as f:
        wr = csv.DictWriter(f, rows[0].keys()); wr.writeheader(); wr.writerows(rows)
w("AreaTable", [{"ID":1,"AreaName_lang":"Testland","ContinentID":0,"ParentAreaID":0},{"ID":2,"AreaName_lang":"Test Camp","ContinentID":0,"ParentAreaID":1}])
w("Map", [{"ID":0,"MapName_lang":"Eastern Kingdoms","InstanceType":0,"WdtFileDataID":900},{"ID":33,"MapName_lang":"Dungeon","InstanceType":1,"WdtFileDataID":901}])
w("UiMap", [{"ID":1429,"Name_lang":"Testland","Type":3}])
O=32*1600/3
w("UiMapAssignment", [{"UiMin_0":0,"UiMin_1":0,"UiMax_0":1,"UiMax_1":1,"Region_0":O-1066.67,"Region_1":O-1066.67,"Region_2":0,"Region_3":O,"Region_4":O,"Region_5":0,"ID":1,"UiMapID":1429,"OrderIndex":0,"MapID":0,"AreaID":1,"WMODoodadPlacementID":0,"WMOGroupID":-1}])
