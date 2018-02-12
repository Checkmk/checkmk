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

#include "SectionSpool.h"
#include <sys/types.h>
#include <experimental/filesystem>
#include "Environment.h"
#include "Logger.h"
#include "WinApiAdaptor.h"
#include "types.h"

namespace fs = std::experimental::filesystem;

extern double file_time(const FILETIME *filetime);

SectionSpool::SectionSpool(const Environment &env, Logger *logger,
                           const WinApiAdaptor &winapi)
    : Section("spool", "spool", env, logger, winapi) {
    withHiddenHeader();
}

bool SectionSpool::produceOutputInner(std::ostream &out) {
    Debug(_logger) << "SectionSpool::produceOutputInner";
    // Look for files in the spool directory and append these files to
    // the agent output. The name of the files may begin with a number
    // of digits. If this is the case then it is interpreted as a time
    // in seconds: the maximum allowed age of the file. Outdated files
    // are simply being ignored.
    //
    time_t now = time(0);

    for (const auto &de : fs::directory_iterator(_env.spoolDirectory())) {
        const auto &path = de.path();
        const auto filename = path.filename().string();
        const int max_age = isdigit(filename[0]) ? atoi(filename.c_str()) : -1;

        if (max_age >= 0) {
            WIN32_FIND_DATA filedata{0};
            SearchHandle searchHandle{
                _winapi.FindFirstFileEx(path.string().c_str(),
                                        FindExInfoStandard, &filedata,
                                        FindExSearchNameMatch, NULL, 0),
                _winapi};
            if (searchHandle) {
                double mtime = file_time(&(filedata.ftLastWriteTime));
                int age = now - mtime;
                if (age > max_age) {
                    Informational(_logger)
                        << "    " << filename
                        << ": skipping outdated file: age is " << age
                        << " sec, "
                        << "max age is " << max_age << " sec.";
                    continue;
                }
            } else {
                Warning(_logger)
                    << "    " << filename << ": cannot determine file age";
                continue;
            }
        }
        Debug(_logger) << "    " << filename;

        std::ifstream ifs(path.string());
        if (ifs) {
            out << ifs.rdbuf();
        }
    }

    return true;
}
