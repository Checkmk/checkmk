#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
# Implement file based locking on Windows.
# Simply exit with 1 if lock file exists (no retry).

from contextlib import contextmanager
import os
import sys
import time
from win32api import GetLastError
from win32event import CreateMutex, ReleaseMutex
from winerror import ERROR_ALREADY_EXISTS

from remote import remotedir

lockname = os.path.join(remotedir, 'test.lock')
mutexname = '__test_lock__'
retry_count = 20


@contextmanager
def synchronized():
    try:
        mutex = CreateMutex(None, True, mutexname)
        if GetLastError() == ERROR_ALREADY_EXISTS:
            sys.stderr.write('Could not acquire mutex. Is another test process running?')
            sys.exit(1)
        yield
    finally:
        if mutex is not None:
            ReleaseMutex(mutex)


def acquire():
    for i in range(retry_count):
        with synchronized():
            if not os.path.exists(lockname):
                open(lockname, 'w').close()
                return
        sys.stderr.write('Lock file exists. Waiting 60s...')
        time.sleep(60)

    sys.stderr.write('Lock file still exists after waiting %d minutes. '
                     'Another test process hung?')
    sys.exit(1)


def release():
    with synchronized():
        os.unlink(lockname)


if __name__ == '__main__':
    commands = {'acquire': acquire, 'release': release}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.stderr.write('Usage: python %s acquire|release' % sys.argv[0])
        sys.exit(1)
    commands[sys.argv[1]]()
