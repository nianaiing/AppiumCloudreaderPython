# -*- coding: utf-8 -*-
import zipfile, struct, sys
sys.stdout.reconfigure(encoding="utf-8")

APK = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\gz神幻\Desktop\安卓项目\capture-apk\WanAndroid_V1.5.apk"
z = zipfile.ZipFile(APK)
data = z.read("AndroidManifest.xml")

# ---------- string pool ----------
sp = 8
scount = struct.unpack_from("<I", data, sp + 8)[0]
flags  = struct.unpack_from("<I", data, sp + 16)[0]
sstart = struct.unpack_from("<I", data, sp + 20)[0]
utf8 = bool(flags & 0x100)
offs = [struct.unpack_from("<I", data, sp + 28 + i * 4)[0] for i in range(scount)]

def read_str(off):
    p = sp + sstart + off
    if utf8:
        v = data[p]; p += 1
        if v & 0x80: p += 2
        v = data[p]; p += 1
        if v & 0x80: p += 2
        end = data.index(b"\x00", p)
        return data[p:end].decode("utf-8", errors="replace")
    length = struct.unpack_from("<H", data, p)[0]
    return data[p+2:p+2+length*2].decode("utf-16le", errors="replace")

strings = [read_str(o) for o in offs]
print("strings:", len(strings))
print("idx 28 =", repr(strings[28]))
print("idx 30 =", repr(strings[30]))
print("idx 31 =", repr(strings[31]))
print("idx 63 =", repr(strings[63]))
print("idx 69 =", repr(strings[69]))

# ---------- resource map ----------
pos = sp
rmap = []
while True:
    ctype, hsize, csize = struct.unpack_from("<HHI", data, pos)
    if ctype == 0x0180:
        n = (csize - hsize) // 4
        rmap = [struct.unpack_from("<I", data, pos + hsize + i * 4)[0] for i in range(n)]
        break
    pos += csize

def st(idx):
    if idx == 0xFFFFFFFF: return "(none)"
    if idx < 0x10000: return strings[idx] if idx < len(strings) else "(pool?)"
    ridx = idx - 0x10000
    return "res:%08x" % rmap[ridx] if ridx < len(rmap) else "(res?)"

# ---------- xml tree ----------
pos = sp
while True:
    ctype, hsize, csize = struct.unpack_from("<HHI", data, pos)
    if ctype in (0x0001, 0x0180):
        pos += csize
        continue
    break

stack = []
activity = None
launcher = False
print("=== activities ===")
while pos < len(data):
    ctype, hsize, csize = struct.unpack_from("<HHI", data, pos)
    if ctype == 0x0102:
        line, comment, ns, name = struct.unpack_from("<IIII", data, pos + 8)
        attrStart, attrSize, attrCount = struct.unpack_from("<HHH", data, pos + 24)
        el = st(name)
        attrs = []
        ap = pos + hsize + attrStart
        for i in range(attrCount):
            ans, aname, araw = struct.unpack_from("<III", data, ap)
            if araw < len(strings):
                val = strings[araw]
            else:
                val = "(typed)"
            attrs.append((st(aname), val))
            ap += attrSize
        stack.append(el)
        if el == "activity":
            activity = attrs
        if el == "action" and any(a[1] == "android.intent.action.MAIN" for a in attrs):
            launcher = True
        if el == "category" and any(a[1] == "android.intent.category.LAUNCHER" for a in attrs):
            launcher = True
    elif ctype == 0x0103:
        el = stack.pop()
        if el == "activity":
            name_attr = next((v for k, v in activity if "name" in k), "?")
            print((">>> LAUNCHER <<< " if launcher else "") + "activity=" + str(name_attr))
            for k, v in activity:
                print("    ", k, "=", v)
            launcher = False
            activity = None
    pos += csize


