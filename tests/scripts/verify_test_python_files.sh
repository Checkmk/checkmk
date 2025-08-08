#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# this script compares the findings of
#  * tests/code_quality/test_python_extensions.py
#  * scripts/find-python-files.sh | grep -v ".py"
# and lists differences.
# It is used to verify, that test_python_extensions.py at least finds the same as the sh version.
set -e

echo "verification of tests/code_quality/test_python_extensions.py and scripts/find-python-files.sh"

# Run the pytest version
test_py_output=$(
    make -C tests test-py-extensions 2>/dev/null | grep "^ -- " | sed 's/.*-- //' | sort
)

echo "$test_py_output" >/tmp/out_test_py.txt

# Run the shell script version
script_sh_output=$(scripts/find-python-files | grep -v ".py" | sort | sed 's/.*master\///')
echo "$script_sh_output" >/tmp/out_script_sh.txt

# Summarize
count1=$(echo "$test_py_output" | wc -l)
count2=$(echo "$script_sh_output" | wc -l)

echo "Summary of Outputs:"
echo "Command 1 (pytest ...): $count1 files"
echo "Command 2 (scripts/find-python-files ...): $count2 files"
echo

# Display diff between outputs
echo "Diff between outputs:"
echo "scripts/find-python-files.sh                                  | tests/code_quality/test_python_extensions.py"
echo "--------------------------------------------------------------x---------------------------------------------"
diff --side-by-side --suppress-common-lines /tmp/out_script_sh.txt /tmp/out_test_py.txt
