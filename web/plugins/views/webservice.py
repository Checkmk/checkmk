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

