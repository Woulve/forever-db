"""Read WoW SavedVariables-style Lua tables into Python (dicts; list-like tables become lists).

load_var(text, "CommandCenterCollect") -> value of that top-level variable, or None.
"""
import re


class _P:
    def __init__(self, s):
        self.s, self.i, self.n = s, 0, len(s)

    def ws(self):
        s, n = self.s, self.n
        while self.i < n:
            c = s[self.i]
            if c in " \t\r\n,;":
                self.i += 1
            elif s.startswith("--", self.i):
                if s.startswith("--[[", self.i):
                    j = s.find("]]", self.i)
                    self.i = n if j < 0 else j + 2
                else:
                    j = s.find("\n", self.i)
                    self.i = n if j < 0 else j + 1
            else:
                break

    def value(self):
        self.ws()
        s, c = self.s, self.s[self.i]
        if c == "{":
            return self.table()
        if c == '"' or c == "'":
            return self.string(c)
        if s.startswith("true", self.i):
            self.i += 4; return True
        if s.startswith("false", self.i):
            self.i += 5; return False
        if s.startswith("nil", self.i):
            self.i += 3; return None
        m = re.compile(r"-?(0x[0-9a-fA-F]+|\d+\.?\d*(e[-+]?\d+)?|\.\d+)").match(s, self.i)
        if not m:
            raise ValueError("bad value at %d: %r" % (self.i, s[self.i:self.i + 30]))
        self.i = m.end()
        t = m.group(0)
        if "x" in t.lower():
            return int(t, 16)
        f = float(t)
        return int(f) if f.is_integer() and "." not in t and "e" not in t.lower() else f

    def string(self, q):
        self.i += 1
        out, s = [], self.s
        while True:
            c = s[self.i]
            if c == "\\":
                nx = s[self.i + 1]
                if nx.isdigit():
                    m = re.compile(r"\d{1,3}").match(s, self.i + 1)
                    out.append(chr(int(m.group(0)))); self.i = m.end(); continue
                out.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "\n": "\n"}.get(nx, nx))
                self.i += 2
            elif c == q:
                self.i += 1
                return "".join(out)
            else:
                out.append(c); self.i += 1

    def table(self):
        self.i += 1
        arr, d, auto = [], {}, 1
        while True:
            self.ws()
            c = self.s[self.i]
            if c == "}":
                self.i += 1
                break
            if c == "[":
                self.i += 1
                k = self.value()
                self.ws()
                assert self.s[self.i] == "]", self.i
                self.i += 1
                self.ws()
                assert self.s[self.i] == "=", self.i
                self.i += 1
                d[k] = self.value()
            else:
                m = re.compile(r"([A-Za-z_]\w*)\s*=(?!=)").match(self.s, self.i)
                if m:
                    self.i = m.end()
                    d[m.group(1)] = self.value()
                else:
                    d[auto] = self.value()
                    auto += 1
        # pure 1..n integer keys -> list
        if d and all(isinstance(k, int) for k in d) and sorted(d) == list(range(1, len(d) + 1)):
            return [d[k] for k in range(1, len(d) + 1)]
        return d if d else []


def load_var(text, name):
    m = re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*", text)
    if not m:
        return None
    p = _P(text)
    p.i = m.end()
    return p.value()


def extract_block(text, name):
    """The raw 'Name = {...}' block of a SavedVariables file (WoW closes top-level tables at column 0)."""
    m = re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*", text)
    if not m:
        return None
    end = re.compile(r"(?m)^\}\s*$").search(text, m.end())
    if not end:
        return None
    return text[m.start():end.end()] + "\n"
