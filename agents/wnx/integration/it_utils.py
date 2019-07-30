from __future__ import print_function
import pytest
import os
import subprocess


# we are checking that input is OK(long enough for example)
def check_actual_input(name, lines, alone, data):
    if data is None:
        pytest.skip('"%s" Data is absent' % name)
        return False

    if not alone:
        lines += 2

    if len(data) < lines:
        pytest.skip('"%s" Data is TOO short:\n %s' % (name, '\n'.join(data)))
        return False

    return True


def safe_binary_remove(binary_path):
    try:
        os.unlink(binary_path)
    except OSError as os_error:
        print("Error %s during file delete" % os_error.errno)


def stop_ohm():
    # stopping all
    subprocess.call("taskkill /F /IM OpenhardwareMonitorCLI.exe")
    subprocess.call("net stop winring0_1_2_0")


def remove_files(target_dir, binaries):
    # removing all
    for f in binaries:
        safe_binary_remove(os.path.join(target_dir, f))


def make_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)
