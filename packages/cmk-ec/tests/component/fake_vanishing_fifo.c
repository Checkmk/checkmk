// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// An LD_PRELOAD fake of open(): A FIFO nobody reads vanishes right after
// opening it fails with ENXIO, like the pipe of a dead Event Console.

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <sys/types.h>
#include <unistd.h>

typedef int (*open_function)(const char *, int, ...);

// This is open() for the linker. With a name of its own for the compiler,
// clang-tidy doesn't insist on the parameter names of <fcntl.h>.
int fake_open(const char *path, int flags, ...) __asm__("open");

int fake_open(const char *path, int flags, ...) {
    // Only these flags come with a mode, see open(2).
    mode_t mode = 0;
    if ((flags & O_CREAT) != 0 || (flags & O_TMPFILE) == O_TMPFILE) {
        va_list args;
        va_start(args, flags);
        mode = va_arg(args, mode_t);
        va_end(args);
    }
    const open_function real_open = (open_function)dlsym(RTLD_NEXT, "open");
    const int fd = real_open(path, flags, mode);
    if (fd == -1 && errno == ENXIO) {
        unlink(path);
        errno = ENXIO;
    }
    return fd;
}
