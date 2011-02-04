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
            tdclass, content = p[0]["paint"](row)
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

    
json_escape = re.compile(r'[\\"\r\n\t\b\f\x00-\x1f]')
json_encoding_table = dict([(chr(i), '\\u%04x' % i) for i in range(32)])
json_encoding_table.update({'\b': '\\b', '\f': '\\f', '\n': '\\n', '\r': '\\r', '\t': '\\t', '\\': '\\\\', '"': '\\"' })

def encode_string_json(s):
    return '"' + json_escape.sub(lambda m: json_encoding_table[m.group(0)], s) + '"'


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
            tdclass, content = p[0]["paint"](row)
            stripped = htmllib.strip_tags(content)
            utf8 = stripped.encode("utf-8")
            html.write(encode_string_json(utf8))
        html.write("]")
    html.write("\n]\n")

multisite_layouts["json"] = {
    "title"  : "JSON data output",
    "render" : render_json,
    "group"  : False,
    "hide"   : True,
}
