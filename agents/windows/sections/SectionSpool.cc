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
#include "../Environment.h"
#include "../LoggerAdaptor.h"
#include <dirent.h>
#include <sys/types.h>
#include <windows.h>


extern double file_time(const FILETIME *filetime);


SectionSpool::SectionSpool(const Environment &env, LoggerAdaptor &logger)
    : Section("spool", env, logger)
{
    withHiddenHeader();
}

bool SectionSpool::produceOutputInner(std::ostream &out) {
    // Look for files in the spool directory and append these files to
    // the agent output. The name of the files may begin with a number
    // of digits. If this is the case then it is interpreted as a time
    // in seconds: the maximum allowed age of the file. Outdated files
    // are simply being ignored.
    //
    DIR *dir = opendir(_env.spoolDirectory().c_str());
    if (dir) {
        WIN32_FIND_DATA filedata;
        char path[512];
        char buffer[4096];
        time_t now = time(0);

        struct dirent *de;
        while (0 != (de = readdir(dir))) {
            char *name = de->d_name;
            if (name[0] == '.') continue;

            snprintf(path, sizeof(path), "%s\\%s", _env.spoolDirectory().c_str(),
                     name);
            int max_age = -1;
            if (isdigit(*name)) max_age = atoi(name);

            if (max_age >= 0) {
                HANDLE h = FindFirstFileEx(path, FindExInfoStandard, &filedata,
                                           FindExSearchNameMatch, NULL, 0);
                if (h != INVALID_HANDLE_VALUE) {
                    double mtime = file_time(&(filedata.ftLastWriteTime));
                    FindClose(h);
                    int age = now - mtime;
                    if (age > max_age) {
                       _logger.crashLog(
                            "    %s: skipping outdated file: age is %d sec, "
                            "max age is %d sec.",
                            name, age, max_age);
                        continue;
                    }
                } else {
                   _logger.crashLog("    %s: cannot determine file age", name);
                    continue;
                }
            }
           _logger.crashLog("    %s", name);

            // Output file in blocks of 4kb
            FILE *file = fopen(path, "r");
            if (file) {
                int bytes_read;
                while (0 < (bytes_read =
                                fread(buffer, 1, sizeof(buffer) - 1, file))) {
                    buffer[bytes_read] = 0;
                    out << buffer;
                }
                fclose(file);
            }
        }
        closedir(dir);
    }
    return true;
}

