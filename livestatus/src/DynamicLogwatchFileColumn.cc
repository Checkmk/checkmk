// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

#include "DynamicLogwatchFileColumn.h"
#include <string.h>
#include <syslog.h>
#include <vector>
#include "HostFileColumn.h"
#include "logger.h"
#include "mk_logwatch.h"
#include "strutil.h"

using namespace std;

// Replace \\ with \ and \s with space
string unescape_filename(string filename)
{
    string filename_native;
    bool quote_active = false;
    for (auto c: filename) {
        if (quote_active) {
            if (c == 's')
                filename_native += ' ';
            else
                filename_native += c;
            quote_active = false;
        }
        else if (c == '\\')
            quote_active = true;
        else
            filename_native += c;
    }
    return filename_native;
}

Column *DynamicLogwatchFileColumn::createColumn(
    int indirect_offset, int extra_offset,
     const char *arguments) {

    // We expect:
    // COLNAME:FILENAME

    // Example:
    // file_contents:var\log\messages

    vector<char> args(arguments, arguments + strlen(arguments) + 1);
    char *scan = &args[0];

    char *colname = next_token(&scan, ':');
    if ((colname == nullptr) || (colname[0] == 0)) {
        logger(LOG_WARNING,
               "Invalid arguments for column %s: missing result column name",
               name());
        return nullptr;
    }

    // Start time of queried range - UNIX time stamp
    char *filename = scan;
    if ((filename == nullptr) || (filename[0] == 0)) {
        logger(LOG_WARNING,
               "Invalid arguments for column %s: missing file name", name());
        return nullptr;
    }

    if (nullptr != strchr(filename, '/')) {
        logger(LOG_WARNING,
               "Invalid arguments for column %s: file name '%s' contains slash",
               name(), filename);
        return nullptr;
    }

    string filename_native = unescape_filename(filename);

    string suffix("/");
    suffix += filename_native;

    return new HostFileColumn(colname, "Contents of logwatch file", MK_LOGWATCH_PATH, suffix.c_str(), indirect_offset, extra_offset);
}
