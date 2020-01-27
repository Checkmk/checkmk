# simple script to patch linux Pipfile to Windows pipfile
# Deprecated now

import sys
import re
from colorama import init, Fore, Back, Style

init()

error_c = Style.BRIGHT + Fore.RED
ok_c = Style.BRIGHT + Fore.GREEN
info_c = Style.BRIGHT + Fore.CYAN

if len(sys.argv) < 2:
    print(error_c + 'Missing arguments')
    exit(1)

try:
    # Read in the file
    print(info_c + "Opening '{}'...".format(sys.argv[1]))
    with open(sys.argv[1], 'r') as file:
        lines = file.readlines()

    # Replace the target string
    with open(sys.argv[1], 'w') as file:
        for l in lines:
            if l.find('python_version = ') == 0:
                file.write('python_version = "3.8" \n')
            elif l.find('psycopg2 = ') == 0:
                file.write('psycopg2 = "*" # windows need new version \n')
            elif l.find('pymssql = ') == 0:
                file.write('# ' + l)
            elif l.find('mysqlclient = ') == 0:
                file.write('# ' + l)
            else:
                file.write(l)

    print(ok_c + 'Finished')
except Exception as e:
    print(error_c + 'Exception is {}'.format(e))
