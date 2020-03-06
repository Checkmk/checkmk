// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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
    void publish(const LogRecord &record) override;
    void rollover();
    bool shouldRollover(std::stringstream &buffer);

    Logger *_logger;
    // The mutex protects the _os.
    std::mutex _mutex;
    const std::string _filename;
    std::ofstream _os;
    const size_t _maxBytes;
    const size_t _backupCount;
    const std::unique_ptr<FileRotationApi> _fileapi;
};

#endif  // RotatingFileHandler_h
