// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "win_error.h"
#include "WinApiAdaptor.h"

std::string get_win_error_as_string(const WinApiAdaptor &winapi,
                                    DWORD error_id /* = GET_LAST_ERROR */) {
    // Get the error message, if any.
    if (error_id == 0) return "No error message has been recorded";
    if (error_id == GET_LAST_ERROR) error_id = winapi.GetLastError();

    LPSTR messageBuffer = NULL;
    size_t size = winapi.FormatMessageA(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM |
            FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL, error_id, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPSTR)&messageBuffer, 0, NULL);

    std::string message(messageBuffer, size);

    // Free the buffer.
    winapi.LocalFree(messageBuffer);

    return message + " (" + std::to_string(error_id) + ")";
}

win_exception::win_exception(const WinApiAdaptor &winapi,
                             const std::string &msg,
                             DWORD error_code /* = GET_LAST_ERROR */)
    : std::runtime_error(msg + "; " +
                         get_win_error_as_string(winapi,
                                                 error_code == GET_LAST_ERROR
                                                     ? winapi.GetLastError()
                                                     : error_code)) {}
