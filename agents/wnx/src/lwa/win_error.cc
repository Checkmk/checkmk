// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "win_error.h"

#include "tools/_raii.h"
#include "types.h"

std::string get_win_error_as_string(DWORD error_id /* = GET_LAST_ERROR */) {
    // Get the error message, if any.
    if (error_id == 0) return "No error message has been recorded";
    if (error_id == GET_LAST_ERROR) error_id = ::GetLastError();

    LPSTR messageBuffer = nullptr;
    size_t size = ::FormatMessageA(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM |
            FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL, error_id, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPSTR)&messageBuffer, 0, NULL);
    ON_OUT_OF_SCOPE(LocalFree(messageBuffer));
    std::string message(messageBuffer, size);

    return message + " (" + std::to_string(error_id) + ")";
}
