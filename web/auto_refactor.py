import re
import sys
from bs4 import BeautifulSoup as bs
from bs4 import NavigableString


def append_to_html(html, indent, addendum):
    return "%s\n%s%s" %(html, ' ' * indent, "%s" % addendum)



def stripper(x):
    x = re.sub(r' %\s+\(.*', '', x)
    index = len(x) - 1
    while index >= 0 and x[index] in ['n', ' ', ')', '"', '\'']:
        if x[index] == 'n' and index > 0 and x[index - 1] == '\\':
            index -= 1
        index -= 1
    return x[:index+1]


def preprocess_tag(tag_str):
    index = 1
    while index + 1< len(tag_str):
        if tag_str[index - 1] == '=' and tag_str[index] not in ['\"', '\'']:
            next_index = index + 1
            while next_index < len(tag_str) and re.match(r'\w', tag_str[next_index]) is not None:
                next_index += 1
            tag_str = tag_str[:index] + '\"' + tag_str[index:(next_index)] + '\"' + tag_str[next_index:]
            index = next_index + 1
        else:
            index += 1
    return tag_str


def add_to_formated_attr_string(attrs, key, val):

    if key in ["class", "id", "type", "for"]:
        key += '_'

    if attrs and key and val:
        attrs += ", "

    if isinstance(val, list):
        val = "[\"" + "\", \"".join(val) + "\"]"
        attrs += "%s=%s" % (key, val)
    else:
        attrs += "%s=\"%s\"" % (key, val)

    return attrs


# Evaluate a tag and its attributes
def eval_tag(tag_str, next_one, next_inbetween):
    skip_next = False
    children = list(bs(tag_str, 'html5lib').body.children)

    if tag_str[1] == '/':
        addendum = "html.close_%s()" % re.sub("<|[/]|>", '' , tag_str)

    elif children and not isinstance(children[0], NavigableString):
        tag_name = ''
        attrs = ''
        tag = children[0]

        tag_name = tag.name
        if "id" in tag.attrs:
            val = tag.attrs.pop("id")
            attrs = add_to_formated_attr_string(attrs, "id", val)

        if "class" in tag.attrs:
            val = tag.attrs.pop("class")
            attrs = add_to_formated_attr_string(attrs, "class", val)

        for key, val in tag.attrs.iteritems():
            attrs = add_to_formated_attr_string(attrs, key, val)

        # See if we can close the tag right away
        if next_one and next_one == ("</%s>" % tag_name):
            addendum = "html.%s(%s%s)" % (tag_name, next_inbetween if next_inbetween else "\'\'", ", " + attrs if attrs else '')
            skip_next = True
        elif tag_name in ['br', 'hr', 'img']:
            addendum = "html.%s(%s)" % (tag_name, attrs)
        else:
            addendum = "html.open_%s(%s)" % (tag_name, attrs)
    else:
            tag_name = tag_str.lstrip(' ').lstrip('<').split(' ')[0].rstrip("/").rstrip(">")
            attrs = tag_str.lstrip(' ').lstrip('<').rstrip(' ').rstrip('>').lstrip(tag_name).lstrip(' ')
            attrs = re.sub(r'class=', "class_=", attrs)
            attrs = re.sub(r'id=', "id_=", attrs)
            attrs = re.sub(r'type=', "type_=", attrs)
            attrs = re.sub(r'for=', "for_=", attrs)
            addendum = "html.open_%s(%s)" % (tag_name, attrs)

    return addendum, skip_next


# replace the input string modulo operator with [[[i]]] where i is the number
# of the current string modulo operator
def replace_inputs(text, inputs):
    for index, input in enumerate(inputs):
        text = re.sub("%" + "s", '[[[%s]]]' % index, text, 1)
    return text


# insert the inputs into the fields where the [[[i]]] space holders are
def insert_inputs(text, inputs):
    if not inputs:
        return text
    replacements = []
    text_index = 0
    for counter, input in enumerate(inputs):
        if "_(" in input and input.count("(") > input.count(")"):
            input += ")"
        if "[[[%s]]]" % counter in text:
            index = text.index("[[[%s]]]" % counter)
            if text[:(index+1)].count('\"') + text[:(index+1)].count('\'') % 2 == 0:
                text = re.sub(r"[[]{3}%s[]]{3}" % counter, input, text, 1)
            else:
                text = re.sub(r"[[]{3}%s[]]{3}" % counter, '%' + 's' + '\" % ' + input + "\"", text, 1)
    return text


def test_replace_inputs():
    text = "<tag class=\"ein %s\" id=%s>%s</tag>"
    inputs = ["test", "id", "Hallo Welt!"]
    print replace_inputs(text, inputs)


# Text extraction
def find_end_of_first_expression(text):
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
    return index


# Split text into a part to refactor and a rest part
def split_html(text):
    index = find_end_of_first_expression(text)
    return text[:index], text[index:]


# this function does a big chunk of the refactoring for me
def replace_is_and_or_in_part(html, indent = 0):

    # I want to refactor only lines with html.write
    if not re.match(".* = .* and .* or ", html.lstrip(' ')):
        return html

    orig_html = html
    print html

    zuweisung, line = html.split(" = ", 1)
    condition, line = line.split(" and ", 1)
    truevalue, line = line.split(" or ")

    # Print string
    try:
        return zuweisung + " = " + truevalue + " if " + condition + " else " + line
    except:
        print "orig_html:\n", orig_html
        print "__________________________________________"
        print "html:\n", html
        print "__________________________________________"
        print "rest:\n", rest
        return zuweisung + " = " + truevalue + " if " + condition + " else " + line


# this function does a big chunk of the refactoring for me
def replace_tags(html, indent = 0):

    # I want to refactor only lines with html.write
    if not html.lstrip(' ').startswith('html.write('):
        return html

    # unbalanced paranthesis indicates sth that goes across line border
    no_comments = '\n'.join(re.sub('#.*', '', line) for line in html.split('\n'))
    if no_comments.count('(') != no_comments.count(')'):
        return html

    # this type of strings is rare and cannot be handeled
    if " % " in html and len(html.split(" % ")) != 2:
        return html

    # split into code to refactor and rest
    html, rest = split_html(html)
    orig_html = html

    # for string inputs find the input arguments
    inputs = []
    if " % " in html or ' %\n' in html:
        if " % " in html:
            html, string_input = html.split(" % ")
        else:
            html, string_input = html.split(" %\n")
        string_input = string_input.lstrip(' ').lstrip("(").rstrip("$").rstrip("\n").rstrip(' ').rstrip(")")
        inputs = string_input.split(",")
        html = replace_inputs(html, inputs) + ")"

    tags = re.findall(r'<[^<]*>', html)
    inbetween = re.split(r'<[^<]*>', re.sub(r'\s*html\.write\([\'|"]?', '', html, 1))
    inbetween = map(stripper, inbetween)

    # if no tags are found, then return unchanged code
    if len(tags) == 0:
        return orig_html + rest

    # First result which is not a tag
    html = ''
    if inbetween[0].strip(' ') not in ['', '\n']:
        html = append_to_html(html, indent, "html.write(%s)" % inbetween[0])

    # Iterate all tags
    counter = 0
    skip_next = False
    while counter < len(tags):
        tag_str = preprocess_tag(tags[counter])
        next_one = tags[counter + 1] if counter + 1 < len(tags) else None
        addendum, skip_next = eval_tag(tag_str, next_one, inbetween[counter + 1])
        html = append_to_html(html, indent, addendum)

        counter += 1

        if not skip_next and inbetween[counter].strip(' ') not in ['', '\n']:
            html = append_to_html(html, indent, "html.write(%s)" % inbetween[counter])
        elif skip_next and addendum.strip(' '):
            counter += 1

    # Now indest the pipes
    html = insert_inputs(html, inputs)
    for index, input in enumerate(inputs):
        if "[[[%s]]]" % index in html:
            html = re.sub("[[[%s]]]" % index, input, html)

    # Print string
    try:
        return orig_html + "(new)\n" + html + rest
    except:
        print "orig_html:\n", orig_html
        print "__________________________________________"
        print "html:\n", html
        print "__________________________________________"
        print "rest:\n", rest
        return orig_html + "(new)\n" + html + "\n" + rest


# indent of a text part which was created using split(html.write).
# This means the indent of the next code block is to be found at the end of the previous block.
def get_indent(text):
    indent = 0
    while indent < len(text) and text[len(text) - 1 - indent] == ' ':
        indent += 1
    return indent


if __name__ == "__main__":

    html = sys.argv[1]
    if html.endswith('.py') and not html.endswith("auto_refactor.py"):

        if len(sys.argv) > 2 and sys.argv[2] == "ifandor":
            with open(html, 'r') as rfile:
                whole_text = rfile.readlines()
            with open(html, "w") as wfile:
                for line in whole_text:
                    wfile.write(replace_is_and_or_in_part(line))

        else:
            with open(html, 'r') as rfile:
                whole_text = "".join(line for line in rfile)

            parts = whole_text.split("html.write(")
            with open("refactored_file.py", "w") as wfile:
                part = parts.pop(0)
                wfile.write(part)

                indent = get_indent(part)
                for part in parts:
                    part = "html.write(" + part
                    wfile.write(replace_tags(part, indent))
                    indent = get_indent(part)

    elif html == "test":
        test_replace_inputs()
    else:
        print replace_tags(html)

