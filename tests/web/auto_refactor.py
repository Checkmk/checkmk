import re
import sys
from bs4 import BeautifulSoup as bs
from bs4 import NavigableString


def eval_tag(tag_str, next_one, next_inbetween):

    skip_next = False
    children = list(bs(tag_str, 'html5lib').body.children)

    if tag_str[1] == '/':
        addendum = "html.close_%s()" % re.sub("<|[/]|>", '' , tag_str)

#    elif '%' + 's' in tag_str: 
#        addendum = ''

    elif children and not isinstance(children[0], NavigableString):
        tag_name = ''
        attrs = ''
        tag = children[0]

        tag_name = tag.name
        for key, val in tag.attrs.iteritems():
            if key in ["class", "id", "type", "for"]:
                key += '_'
            if attrs and key and val:
                attrs += ", "
            if isinstance(val, list):
                val = "[\"" + "\", \"".join(val) + "\"]"
                attrs += "%s=%s" % (key, val)
            else:
                attrs += "%s=\"%s\"" % (key, val)

        # See if we can close the tag right away
        if next_one and next_one[1] == '/' and next_one == ("</%s>" % tag_name):
            addendum = "html.%s(%s%s)" % (tag_name, next_inbetween, ", " + attrs if attrs else '')
            skip_next = True
        elif tag_name in ['br', 'hr', 'img']:
            addendum = "html.%s(%s)" % (tag_name, attrs)
        else:
            addendum = "html.open_%s(%s)" % (tag_name, attrs)
    else:
            tag_name = tag_str.lstrip(' ').lstrip('<').split(' ')[0].rstrip("/").rstrip(">")
            attrs = tag_str.lstrip(' ').lstrip('<').rstrip(' ').rstrip('>').lstrip(tag_name)
            addendum = "html.open_%s(%s)" % (tag_name, attrs)

    return addendum, skip_next


def append_to_html(html, indent, addendum):
    return "%s\n%s%s" %(html, ' ' * indent, "%s" % addendum)


def split_html(text):
    index = 1
    while index < len(text) and text[index - 1] != "(":
        index += 1
    open_braces = 1
    while index < len(text) and open_braces > 0:
        if text[index] == "(":
            open_braces += 1
        elif text[index] == ")":
            open_braces -= 1
        index += 1
    while index < len(text) and text[index] != "\n":
        index += 1
    return text[:index], text[index:]


def stripper(x):
    x = re.sub(r' %\s+\(.*', '', x)
    index = len(x) - 1
    while index >= 0 and x[index] in ['n', ' ', ')', '"', '\'']:
        if x[index] == 'n' and index > 0 and x[index - 1] == '\\':
            index -= 1
        index -= 1
    return x[:index+1]


# this function does a big chunk of the refactoring for me
def replace_tags(html, indent = 0):

    # I want to refactor only lines with html.write
    if not html.lstrip(' ').startswith('html.write('):
        return html

    # unbalanced paranthesis indicates sth that goes across line border
    if html.count('(') != html.count(')'):
        return html

    html, rest = split_html(html)
    orig_html = html

    # strip all comments
    html = re.sub(r'#.*', '', html)

    if len(html.split(" % ")) == 2:
        html, string_input = html.split(" % ")
        string_input = string_input.lstrip("(").rstrip("$").rstrip("\n").rstrip(' ').rstrip(")")
        for input in string_input.split(","):
            if ("%" + "s") in html:
                html = re.sub("%" + "s", input, html, 1)

    tags = re.findall(r'<[^<]*>', html)
    if len(tags) == 0:
        return orig_html + rest

    inbetween = re.split(r'<[^<]*>', re.sub(r'\s*html\.write\([\'|"]?', '', html, 1))
    inbetween = map(stripper, inbetween)

    html = orig_html + "\n(new)"

    if inbetween[0].strip(' ') not in ['', '\n']:
        html = append_to_html(html, indent, "html.write(%s)" % inbetween[0])

    # Iterate all tags
    counter = 0
    skip_next = False
    while counter < len(tags):
        tag_str = tags[counter]
        next_one = tags[counter + 1] if counter + 1 < len(tags) else None
        addendum, skip_next = eval_tag(tag_str, next_one, inbetween[counter + 1])
        if not skip_next and addendum.strip(' '):
            html = append_to_html(html, indent, addendum)

        counter += 1

        if not skip_next and inbetween[counter].strip(' ') not in ['', '\n']:
            html = append_to_html(html, indent, "html.write(%s)" % inbetween[counter])

    try:
        return html + "\n(/new)" + rest
    except:
        print "html:\n", html
        print "__________________________________________"
        print "rest:\n", rest
        return html + "\n(/new)" + rest

import re
html = sys.argv[1]
if html.endswith('.py'):
    whole_text = ''
    with open(html, 'r') as rfile:
        whole_text = "".join(line for line in rfile)
    parts = whole_text.split("html.write(")
    with open("refactored_file.py", "w") as wfile:
        part = parts.pop(0)
        wfile.write(part)
        indent = 0
        while indent < len(part) and part[len(part) - 1 - indent] == ' ':
            indent += 1
        for part in parts:
            part = "html.write(" + part
            wfile.write(replace_tags(part, indent))
            indent = 0
            while indent < len(part) and part[len(part) - 1 - indent] == ' ':
                indent += 1
else:
    print replace_tags(html)

