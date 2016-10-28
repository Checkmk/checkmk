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
from tools import compare_html , gentest, compare_and_empty
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

    with open(autotest_filename, 'w') as auto:
        auto.write(header)
        with open(sys.argv[1], 'r') as diff:
            for line in diff:

                if re.match(r'@@.*', line):
                    if counter > 0:
                        auto.write(function_end)
                    auto.write(function_start(counter))
                    counter += 1
                    continue

                elif counter == 0 or len(line) <= 1:
                    continue

                if not re.match(r'[+|-].+', line):
                    continue

                if not re.match(r'[+|-].+', line) and line[0] not in ['+', '-']:
                    auto.write(line[1:])

                elif re.match(r'[+]{3}.*', line) or re.match(r'[-]{3}.*', line):
                    continue

                elif re.match(r'[-]\s*html\..*', line):
                    pattern = re.compile(r'[-]\s*html\.')
                    auto.write(re.sub(r'\s*html\.', '    old.', line[1:], count=1))

                elif re.match(r'[+]\s*html\..*', line):
                    pattern = re.compile(r'\s*html\.')
                    auto.write(pattern.sub('    new.', line[1:], count=1))

                else:
                    auto.write(line[1:])

        if(counter > 0):
            auto.write(function_end)
