"""AllTheThings' C# parser preprocesses each Lua data file with comment directives
(`-- #if FOREVER`, `-- #if AFTER TBC`, `-- #if NOT ANYCLASSIC`, `-- #else`, `-- #endif`).
This applies them the way the Forever build does: inactive lines become empty lines (so
line numbers in error messages still match).

Forever's build: tags ANYCLASSIC FOREVER CAMELOT CLASSIC CRIEVE EXPLORATION OBJECTIVES
NOSIMPLIFY, data patch 1.60.1 - every "AFTER <expansion/patch>" is false and every
"BEFORE <later patch>" is true.
"""
import re

TAGS = {"ANYCLASSIC", "FOREVER", "CAMELOT", "CLASSIC", "CRIEVE", "EXPLORATION", "OBJECTIVES", "NOSIMPLIFY"}
PATCH = (1, 60, 1)
EXPANSIONS = {"CLASSIC": (1, 0, 0), "TBC": (2, 0, 1), "WRATH": (3, 0, 2), "CATA": (4, 0, 1), "MOP": (5, 0, 4),
              "WOD": (6, 0, 2), "LEGION": (7, 0, 3), "BFA": (8, 0, 1), "SHADOWLANDS": (9, 0, 1), "SL": (9, 0, 1),
              "DF": (10, 0, 2), "TWW": (11, 0, 2), "MIDNIGHT": (12, 0, 0), "MID": (12, 0, 0)}
DIRECTIVE = re.compile(r"^\s*--\s*#\s*(if|ifdef|ifndef|elseif|elif|else|endif)\b(.*)$", re.I)


def version(tok):
    tok = tok.upper()
    if tok in EXPANSIONS:
        return EXPANSIONS[tok]
    m = re.fullmatch(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", tok)
    if m:
        return tuple(int(x or 0) for x in m.groups())
    return None


def evaluate(expr):
    expr = expr.strip()
    toks = expr.replace("(", " ( ").replace(")", " ) ").split()
    pos = 0

    def peek():
        return toks[pos].upper() if pos < len(toks) else None

    def take():
        nonlocal pos
        t = toks[pos]
        pos += 1
        return t

    def atom():
        t = peek()
        if t is None:
            return False
        if t == "(":
            take()
            v = orexpr()
            if peek() == ")":
                take()
            return v
        if t == "NOT" or t == "!":
            take()
            return not atom()
        if t in ("AFTER", "BEFORE"):
            take()
            v = version(take()) if pos < len(toks) else None
            if v is None:
                return False
            return PATCH >= v if t == "AFTER" else PATCH < v
        take()
        if t in TAGS:
            return True
        v = version(t)
        if v is not None:                      # "#if MOP" = that expansion or later
            return PATCH >= v
        return False

    def andexpr():
        v = atom()
        while peek() in ("AND", "&&"):
            take()
            v = atom() and v
        return v

    def orexpr():
        v = andexpr()
        while peek() in ("OR", "||"):
            take()
            v = andexpr() or v
        return v

    return orexpr()


def preprocess(text):
    out = []
    stack = []          # (parent_active, branch_taken, active)
    active = True
    for line in text.split("\n"):
        m = DIRECTIVE.match(line)
        if not m:
            out.append(line if active else "")
            continue
        kind, rest = m.group(1).lower(), m.group(2)
        if kind in ("if", "ifdef", "ifndef"):
            cond = evaluate(rest)
            if kind == "ifndef":
                cond = not cond
            stack.append((active, cond))
            active = active and cond
        elif kind in ("elseif", "elif"):
            if stack:
                parent, taken = stack[-1]
                cond = (not taken) and evaluate(rest)
                stack[-1] = (parent, taken or cond)
                active = parent and cond
        elif kind == "else":
            if stack:
                parent, taken = stack[-1]
                stack[-1] = (parent, True)
                active = parent and not taken
        elif kind == "endif":
            if stack:
                active = stack.pop()[0]
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        print(preprocess(open(p, encoding="utf-8-sig").read()))
