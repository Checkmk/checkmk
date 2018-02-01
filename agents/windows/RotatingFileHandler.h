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

#ifndef RotatingFileHandler_h
#define RotatingFileHandler_h

#include <sstream>
#include "Logger.h"

class FileRotationApi {
public:
    virtual ~FileRotationApi() = default;

    virtual bool fileExists(const std::string &filename) const;
    virtual bool remove(const std::string &filename) const;
    virtual bool rename(const std::string &oldFilename,
                        const std::string &newFilename) const;
};

class RotatingFileHandler : public Handler {
public:
    RotatingFileHandler(const std::string &filename,
                        std::unique_ptr<FileRotationApi> fileapi,
                        size_t maxBytes = 0, size_t backupCount = 0);
    RotatingFileHandler(const RotatingFileHandler &) = delete;
    RotatingFileHandler &operator=(const RotatingFileHandler &) = delete;

private:
    Logger *_logger;
    // The mutex protects the _os.
    std::mutex _mutex;
    const std::string _filename;
    std::ofstream _os;
    const size_t _maxBytes;
    const size_t _backupCount;
    const std::unique_ptr<FileRotationApi> _fileapi;

    void publish(const LogRecord &record) override;
    void rollover();
    bool shouldRollover(std::stringstream &buffer);
};

#endif  // RotatingFileHandler_h
