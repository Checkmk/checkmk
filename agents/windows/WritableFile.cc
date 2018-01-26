// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
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

#include "WritableFile.h"
#include <algorithm>
#include "Environment.h"
#include "Logger.h"
#include "win_error.h"

std::string FileError::constructMessage(const std::string &path,
                                        const std::string &what) const {
    return "File '" + path + "': error: " + what;
}

WritableFile::WritableFile(const std::string &filePath, DWORD shareMode,
                           DWORD disposition, const WinApiAdaptor &winapi)
    : _path(filePath)
    , _hFile{winapi.CreateFile(_path.c_str(),  // file to open
                               GENERIC_WRITE,  // open for write
                               shareMode,
                               nullptr,  // default security
                               disposition,
                               FILE_ATTRIBUTE_NORMAL,  // normal file
                               nullptr),               // no attr. template
             winapi}
    , _winapi(winapi) {
    if (!_hFile) {
        throw FileError(_path, get_win_error_as_string(_winapi));
    }
}

WritableFile &WritableFile::operator<<(const std::string &s) {
    DWORD written = 0;
    if (!_winapi.WriteFile(_hFile.get(), s.c_str(), s.size(), &written,
                           nullptr)) {
        throw FileError(_path, get_win_error_as_string(_winapi));
    }
    return *this;
}

std::unordered_set<std::string> getDefaultWhitelist(
    const Environment &env, const WinApiAdaptor &winapi) {
    std::unordered_set<std::string> whitelist = {
        env.agentDirectory() + "\\bin\\OpenHardwareMonitorLib.sys"};
    std::vector<char> path(_MAX_PATH, '\0');

    if (winapi.GetModuleFileName(nullptr, path.data(), path.size())) {
        whitelist.emplace(path.data());
    }

    return whitelist;
}

bool areAllFilesWritable(const std::string &dirPath,
                         const WinApiAdaptor &winapi,
                         const std::unordered_set<std::string> &whitelist) {
    std::string tmp = dirPath + "\\*";
    WIN32_FIND_DATA file{0};
    std::vector<std::string> directories;
    SearchHandle searchHandle{winapi.FindFirstFile(tmp.c_str(), &file), winapi};

    if (searchHandle) {
        do {
            auto fullPath = dirPath + "\\" + file.cFileName;

            if (file.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                if ((!strcmp(file.cFileName, ".")) ||
                    (!strcmp(file.cFileName, ".."))) {
                    continue;
                } else {
                    directories.push_back(std::move(fullPath));
                }
            } else {
                if (whitelist.find(fullPath) == whitelist.end()) {
                    WritableFile writableFile(
                        fullPath, FILE_SHARE_READ | FILE_SHARE_WRITE,
                        OPEN_EXISTING, winapi);
                }
            }
        } while (winapi.FindNextFile(searchHandle.get(), &file));
    }

    return std::all_of(directories.cbegin(), directories.cend(),
                       [&winapi, &whitelist](const std::string &dir) {
                           return areAllFilesWritable(dir, winapi, whitelist);
                       });
}
