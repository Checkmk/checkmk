def mangle_version(v):
    for i, c in enumerate(v.elems()):
        if not c.isdigit() and not c == ".":
            return v[:i]

    return v
