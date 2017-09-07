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

#include "SectionFileinfo.h"
#include <cstring>
#include <iomanip>
#include <sstream>

extern double current_time();
extern double file_time(const FILETIME *filetime);

SectionFileinfo::SectionFileinfo(Configuration &config, Logger *logger,
                                 const WinApiAdaptor &winapi)
    : Section("fileinfo", config.getEnvironment(), logger, winapi)
    , _fileinfo_paths(config, "fileinfo", "path", winapi) {
    withSeparator('|');
}

bool SectionFileinfo::produceOutputInner(std::ostream &out) {
    out << std::fixed << std::setprecision(0) << current_time() << "\n";

    for (const std::string &path : *_fileinfo_paths) {
        outputFileinfos(out, path.c_str());
    }

    return true;
}

void SectionFileinfo::get_directories(std::string base_path) {
    WIN32_FIND_DATA findData;
    HANDLE findHandle;

    std::stringstream ss;
    ss << base_path << "\\"
       << "*.*";
    if ((findHandle = _winapi.FindFirstFile(ss.str().c_str(), &findData)) !=
        INVALID_HANDLE_VALUE) {
        do {
            if (strcmp(findData.cFileName, ".") &&
                strcmp(findData.cFileName,
                       ".."))  // Skip Root (..) and current (.) dir
            {
                ss.str("");
                ss.clear();
                ss << base_path << "\\" << findData.cFileName;
                if (findData.dwFileAttributes &
                    FILE_ATTRIBUTE_DIRECTORY)  // Directory found
                    get_directories(ss.str());
                else
                    _temp_files.push_back(ss.str());
            }
        } while (_winapi.FindNextFile(findHandle, &findData));
        _winapi.FindClose(findHandle);
    }
}

void SectionFileinfo::determine_filepaths_full_search(
    std::string base_path, std::string search_pattern) {
    get_directories(base_path);
    for (auto entry : _temp_files) {
        if (globmatch(search_pattern.c_str(), entry.c_str())) {
            _found_files.push_back(entry);
        }
    }
    _temp_files.clear();
}

void SectionFileinfo::determine_filepaths_simple_search(
    std::string base_path, std::string search_pattern) {
    WIN32_FIND_DATA data;
    auto findHandle =
        _winapi.FindFirstFileEx(search_pattern.c_str(), FindExInfoStandard,
                                &data, FindExSearchNameMatch, NULL, 0);

    std::stringstream ss;
    if (findHandle != INVALID_HANDLE_VALUE) {
        do {
            if (0 == (data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                ss.str("");
                ss.clear();
                ss << base_path << "\\" << data.cFileName;
                _found_files.push_back(ss.str());
            }
        } while (_winapi.FindNextFile(findHandle, &data));
        _winapi.FindClose(findHandle);
    }
}

void SectionFileinfo::determine_filepaths(std::string search_pattern) {
    auto pos_asterisk = search_pattern.find("*");
    auto pos_question_mark = search_pattern.find("?");
    auto pos_backslash = search_pattern.find_last_of("\\");
    auto pos_min_glob = std::min(pos_asterisk, pos_question_mark);

    auto subpattern = search_pattern.substr(0, pos_min_glob);
    auto base_path = subpattern.substr(0, subpattern.find_last_of("\\"));

    if (pos_backslash > pos_min_glob) {
        determine_filepaths_full_search(base_path, search_pattern);
    } else {
        determine_filepaths_simple_search(base_path, search_pattern);
    }
}

void SectionFileinfo::outputFileinfos(std::ostream &out, const char *path) {
    std::string search_pattern(path);
    _found_files.clear();

    determine_filepaths(search_pattern);

    bool found_file = false;
    for (auto entry : _found_files) {
        found_file = outputFileinfo(out, entry) || found_file;
    }

    if (!found_file) {
        out << path << "|missing|" << current_time() << "\n";
    }
}

bool SectionFileinfo::outputFileinfo(std::ostream &out,
                                     const std::string filename) {
    WIN32_FIND_DATA findData;
    HANDLE findHandle;
    if ((findHandle = _winapi.FindFirstFile(filename.c_str(), &findData)) !=
        INVALID_HANDLE_VALUE) {
        unsigned long long size =
            (unsigned long long)findData.nFileSizeLow +
            (((unsigned long long)findData.nFileSizeHigh) << 32);
        out << filename << "|" << size << "|" << std::fixed
            << std::setprecision(0) << file_time(&findData.ftLastWriteTime)
            << "\n";
        _winapi.FindClose(findHandle);
        return true;
    }
    return false;
}
