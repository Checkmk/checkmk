// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

#include "SectionFileinfo.h"
#include <iomanip>

extern double current_time();
extern double file_time(const FILETIME *filetime);

SectionFileinfo::SectionFileinfo(Configuration &config)
    : Section("fileinfo")
    , _fileinfo_paths(config, "fileinfo", "path")
{
    withSeparator('|');
}


bool SectionFileinfo::produceOutputInner(std::ostream &out,
                                         const Environment &env) {
    out << std::fixed << std::setprecision(0) << current_time() << "\n";

    for (const std::string &path : *_fileinfo_paths) {
        outputFileinfos(out, path.c_str());
    }

    return true;
}

void SectionFileinfo::outputFileinfos(std::ostream &out, const char *path) {
    WIN32_FIND_DATA data;
    HANDLE h = FindFirstFileEx(path, FindExInfoStandard, &data,
                               FindExSearchNameMatch, NULL, 0);
    bool found_file = false;

    if (h != INVALID_HANDLE_VALUE) {
        // compute basename of path: search backwards for '\'
        const char *basename = "";
        char *end = strrchr(path, '\\');
        if (end) {
            *end = 0;
            basename = path;
        }
        found_file = outputFileinfo(out, basename, &data);
        while (FindNextFile(h, &data))
            found_file = outputFileinfo(out, basename, &data) || found_file;
        if (end) *end = '\\';  // repair string
        FindClose(h);

        if (!found_file) {
            out << path << "|missing|" << current_time() << "\n";
        }
    } else {
        DWORD e = GetLastError();
        out << path << "|missing|" << e << "\n";
    }
}

bool SectionFileinfo::outputFileinfo(std::ostream &out, const char *basename,
                                     WIN32_FIND_DATA *data) {
    uint64_t size = to_u64(data->nFileSizeLow, data->nFileSizeHigh);

    if (0 == (data->dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
        out << basename << "\\" << data->cFileName << "|" << size << "|"
            << std::fixed << std::setprecision(0)
            << file_time(&data->ftLastWriteTime) << "\n";
        return true;
    }
    return false;
}

