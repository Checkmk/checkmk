// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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
                           DWORD disposition, const WinApiInterface &winapi)
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

WritableFile &WritableFile::operator<<(const std::vector<BYTE> &s) {
    DWORD written = 0;
    if (!_winapi.WriteFile(_hFile.get(), s.data(), s.size(), &written,
                           nullptr)) {
        throw FileError(_path, get_win_error_as_string(_winapi));
    }
    return *this;
}

std::unordered_set<std::string> getDefaultWhitelist(
    const Environment &env, const WinApiInterface &winapi) {
    std::unordered_set<std::string> whitelist = {
        env.agentDirectory() + "\\bin\\OpenHardwareMonitorLib.sys"};
    std::vector<char> path(_MAX_PATH, '\0');

    if (winapi.GetModuleFileName(nullptr, path.data(), path.size())) {
        whitelist.emplace(path.data());
    }

    return whitelist;
}

bool areAllFilesWritable(const std::string &dirPath,
                         const WinApiInterface &winapi,
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
