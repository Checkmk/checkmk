def render_python_raw(data, view, group_painters, painters, num_columns):
    html.write(repr(data))

multisite_layouts["python-raw"] = {
    "title"  : "Python raw data output",
    "render" : render_python_raw,
    "group"  : False,
    "hide"   : True,
}

def render_python(data, view, group_painters, painters, num_columns):
    columns, rows = data
    html.write("[\n")
    html.write(repr([p[0]["title"] for p in painters]))
    html.write(",\n")
    for row in rows:
        html.write("[")
        for p in painters:
            tdclass, content = prepare_paint(p, row)
            html.write(repr(htmllib.strip_tags(content)))
            html.write(",")
        html.write("],")
    html.write("\n]\n")

multisite_layouts["python"] = {
    "title"  : "Python data output",
    "render" : render_python,
    "group"  : False,
    "hide"   : True,
}

def render_json(data, view, group_painters, painters, num_columns):
    columns, rows = data
    html.write("[\n")
    html.write(repr([p[0]["title"] for p in painters]))
    for row in rows:
        html.write(",\n[")
        first = True
        for p in painters:
            if first:
                first = False
            else:
                html.write(",")
            tdclass, content = prepare_paint(p, row)
            stripped = htmllib.strip_tags(content)
            utf8 = stripped.encode("utf-8")
            html.write(repr(utf8))
        html.write("]")
    html.write("\n]\n")

multisite_layouts["json"] = {
    "title"  : "JSON data output",
    "render" : render_json,
    "group"  : False,
    "hide"   : True,
}
