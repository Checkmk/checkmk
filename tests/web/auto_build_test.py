#!/usr/bin/python

#
# This little script can be used to semi-automatically generate a test file for the
# refactoring process.
# It expects a 'git diff master refactored_file.py' printout and generates test functions
# for every individual replacement.
# It is semi-automativ, because the generated 'test_auto_refactored_file.py needs to be postprocessed
# by adding variables and adjusting the indent level for if clauses for example.
# then the file can be called using py.test -s -v test_auto_refactored_file.py
#

import sys, re
import os.path

header = '''
#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# enable imports from web directory
from testlib import cmk_path
import sys
sys.path.insert(0, "%s/web/htdocs" % cmk_path())

# external imports
import re
from bs4 import BeautifulSoup as bs

# internal imports
from classes import HTMLOrigTester, HTMLCheck_MKTester
from tools import compare_html, gentest, compare_and_empty

_ = lambda x: x

title = "title"
key = "key"
name = "name"
vp = "vp"
varprefix = "varprefix"
prefix = "prefix"
css = "css"
cls = "cls"
disp = "disp"
sel = "selected"
div_id = "div1"

_vertical = "vertical"
_delete_style = "filter"
_label = "label"
_empty_text = "empty text"
_no_elements_text = _empty_text
_columns = 5
_size = 10

select_func = "selector"
unselect_func = "unselector"
active_category = "active_category"
category_name = "active_category"
category_alias = "active_alias"

div_is_open = True
visible = True
oneline = True

mod = 2
nr = 1
indent = 10
display_off = "none"
display_on = "row"

classes = ["cls1", "cls2"]
#onclick = "onclick_code('<lol>');"
onclick = "onclick_code('lol');"
title   = "Title"
thclass = "th"
tdclass = "th"
content = "<tag> content </tag>"
tdattrs= "class='tdclass'"
is_open = True
option  = "option"
icon    = "icon"
value   = "Testvalue"
view    = {"name": "viewname"}
choices = ["c1", "c2"]
hidden  = True
id      = "id"
e       = "error"
query   = "Hallo Welt!"
'''

function_start = lambda x: '''
def test_%d():
    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()
\n
''' % x

function_end = '''
    compare_and_empty(old, new)

'''


if __name__ == "__main__":

    if len(sys.argv) <= 1:
        print "ERROR GIVE A FILE PLS"
        exit(0)

    test_name = re.sub(r'\..*', '', sys.argv[1])
    test_name = re.sub(r'diff_', '', test_name)
    autotest_filename = 'test_auto_%s.py' % test_name

    # Dialogue
    if os.path.isfile(autotest_filename):
        replace = raw_input("Do you want to replace the existing auto test file %s? [Y/N]" % autotest_filename)
        while replace not in ['y', 'Y', 'n', 'N']:
           replace = raw_input("Please enter either 'Y' of 'N'!")
        if replace in ['n', 'N']:
            print 'Aborting..'
            exit(0)

    counter = 0
    indent = ' ' * 4

    with open(autotest_filename, 'w') as auto:
        auto.write(header)
        with open(sys.argv[1], 'r') as diff:

            old_line = []
            new_line = []

            for line in diff:

                line = line[0] + line[1:].lstrip(' ')

                if re.match(r'@@.*', line):
                    if counter > 0:
                        auto.write(indent + indent.join(old_line))
                        auto.write(indent + indent.join(new_line))
                        auto.write("\n\n")
                        auto.write(function_end)
                        old_line = []
                        new_line = []
                    auto.write(function_start(counter))
                    counter += 1
                    continue

                elif counter == 0 or len(line) <= 1:
                    continue

                if not re.match(r'[+|-].+', line):
                    continue

                if not re.match(r'[+|-].+', line) and line[0] not in ['+', '-']:
                    old_line.append(line[1:])
                    new_line.append(line[1:])

                elif re.match(r'[+]{3}.*', line) or re.match(r'[-]{3}.*', line):
                    continue

                elif re.match(r'[-]\s*html\..*', line):
                    pattern = re.compile(r'[-]\s*html\.')
                    old_line.append(re.sub(r'\s*html\.', 'old.', line[1:], count=1))

                elif re.match(r'[+]\s*html\..*', line):
                    pattern = re.compile(r'\s*html\.')
                    new_line.append(pattern.sub('new.', line[1:], count=1))

                elif re.match(r'[-].*', line):
                    old_line.append(line[1:])

                elif re.match(r'[+].*', line):
                    new_line.append(line[1:])

                else:
                    print line

        if(counter > 0):
            auto.write(indent + indent.join(old_line))
            auto.write(indent + indent.join(new_line))
            auto.write("\n\n")
            auto.write(function_end)
