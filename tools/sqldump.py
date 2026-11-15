"""Minimal MySQL dump reader: CREATE TABLE column lists + INSERT rows, no MySQL needed.

read_tables(paths, wanted) -> {table_name: {"cols": [lowercase names], "rows": [tuple, ...]}}
Handles multi-row INSERTs, INSERT with explicit column lists, quoted strings with escapes,
NULL, numbers, and .sql / .sql.gz / .zip inputs.
"""
import gzip, io, re, zipfile, os

CREATE_RE = re.compile(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?`?(\w+)`?\s*\(", re.I)
INSERT_RE = re.compile(r"INSERT\s+(?:IGNORE\s+)?INTO\s+`?(\w+)`?\s*(\(([^)]*)\))?\s*VALUES\s*", re.I)
COL_RE = re.compile(r"^\s*`(\w+)`\s+\w+", re.I)


def _open_texts(path):
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.lower().endswith(".sql"):
                    yield io.TextIOWrapper(z.open(n), encoding="utf-8", errors="replace")
    elif path.endswith(".gz"):
        yield gzip.open(path, "rt", encoding="utf-8", errors="replace")
    else:
        yield open(path, "r", encoding="utf-8", errors="replace")


def _parse_values(s, i):
    """Parse '(..),(..);' starting at s[i]; return (rows, index after ';')."""
    rows, n = [], len(s)
    while i < n:
        while i < n and s[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        if s[i] == ";":
            return rows, i + 1
        if s[i] != "(":
            raise ValueError("bad VALUES at %d: %r" % (i, s[i:i + 40]))
        i += 1
        row, cur = [], None
        while True:
            c = s[i]
            if c == "'":
                i += 1
                buf = []
                while True:
                    c = s[i]
                    if c == "\\":
                        nx = s[i + 1]
                        buf.append({"n": "\n", "r": "\r", "t": "\t", "0": "\0"}.get(nx, nx))
                        i += 2
                    elif c == "'":
                        if s[i + 1] == "'":
                            buf.append("'"); i += 2
                        else:
                            i += 1; break
                    else:
                        buf.append(c); i += 1
                cur = "".join(buf)
            elif c in ",)":
                if isinstance(cur, str) and not getattr(cur, "_q", False):
                    pass
                row.append(cur)
                cur = None
                i += 1
                if c == ")":
                    break
            elif c in " \t\r\n":
                i += 1
            else:
                j = i
                while s[j] not in ",)":
                    j += 1
                tok = s[i:j].strip()
                i = j
                if tok.upper() == "NULL":
                    cur = None
                else:
                    try:
                        cur = int(tok)
                    except ValueError:
                        try:
                            cur = float(tok)
                        except ValueError:
                            cur = tok
        rows.append(tuple(row))
    return rows, i


def read_tables(paths, wanted=None):
    wanted = {w.lower() for w in wanted} if wanted else None
    out = {}
    for path in paths:
        for f in _open_texts(path):
            text = f.read()
            # columns from CREATE TABLE
            for m in CREATE_RE.finditer(text):
                name = m.group(1).lower()
                if wanted and name not in wanted:
                    continue
                depth, j = 1, m.end()
                while depth and j < len(text):
                    if text[j] == "(":
                        depth += 1
                    elif text[j] == ")":
                        depth -= 1
                    j += 1
                cols = []
                body, parts, d2, cur = text[m.end():j - 1], [], 0, []
                for ch in body:                       # split on commas outside parentheses
                    if ch == "(":
                        d2 += 1
                    elif ch == ")":
                        d2 -= 1
                    if ch == "," and d2 == 0:
                        parts.append("".join(cur)); cur = []
                    else:
                        cur.append(ch)
                parts.append("".join(cur))
                for part in parts:
                    cm = COL_RE.match(part.strip())
                    if cm:
                        cols.append(cm.group(1).lower())
                t = out.setdefault(name, {"cols": cols, "rows": []})
                if not t["cols"]:
                    t["cols"] = cols
            for m in INSERT_RE.finditer(text):
                name = m.group(1).lower()
                if wanted and name not in wanted:
                    continue
                rows, _ = _parse_values(text, m.end())
                t = out.setdefault(name, {"cols": [], "rows": []})
                if m.group(3):
                    cols = [c.strip().strip("`").lower() for c in m.group(3).split(",")]
                    if not t["cols"]:
                        t["cols"] = cols
                    elif cols != t["cols"]:
                        idx = [cols.index(c) if c in cols else None for c in t["cols"]]
                        rows = [tuple(r[k] if k is not None else None for k in idx) for r in rows]
                t["rows"].extend(rows)
    return out


class Table:
    """Row access by (case-insensitive) column name, with fallbacks: t.get(row, 'Entry', 'entry')."""

    def __init__(self, raw):
        self.cols = raw["cols"] if raw else []
        self.rows = raw["rows"] if raw else []
        self.idx = {c.lower(): k for k, c in enumerate(self.cols)}

    def col(self, *names):
        for n in names:
            k = self.idx.get(n.lower())
            if k is not None:
                return k
        return None

    def has(self, *names):
        return self.col(*names) is not None

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)


def find_dumps(folder):
    res = []
    for root, _, files in os.walk(folder):
        for fn in files:
            if fn.lower().endswith((".sql", ".sql.gz", ".zip")):
                res.append(os.path.join(root, fn))
    return sorted(res)
