// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "RotatingFileHandler.h"
#include <sys/stat.h>
#include <cstdio>

using std::endl;
using std::flush;
using std::lock_guard;
using std::mutex;
using std::ofstream;
using std::ostringstream;
using std::string;
using std::stringstream;

// TODO: replace this old C based implementation with
// std(::experimental)::filesystem as soon as we upgrade to a MinGW version
// supporting it.

bool FileRotationApi::fileExists(const string &filename) const {
#ifdef __WIN32
    struct _stat buffer;
    const int result = _stat(filename.c_str(), &buffer);
#else
    struct stat buffer;
    const int result = stat(filename.c_str(), &buffer);
#endif
    return result == 0;
}

bool FileRotationApi::remove(const string &filename) const {
    return std::remove(filename.c_str()) == 0;
}

bool FileRotationApi::rename(const string &oldFilename,
                             const string &newFilename) const {
    return std::rename(oldFilename.c_str(), newFilename.c_str()) == 0;
}

RotatingFileHandler::RotatingFileHandler(
    const string &filename, std::unique_ptr<FileRotationApi> fileapi,
    size_t maxBytes /*=0*/, size_t backupCount /*=0*/)
    // Let us use our own logger instance that writes to stderr as
    // we only want to log serious errors that we cannot print to
    // the logfile that we should be handling ourselves!
    : _logger(Logger::getLogger("RotatingFileHandler"))
    , _filename(filename)
    , _os(filename, ofstream::app)
    , _maxBytes(maxBytes)
    , _backupCount(backupCount)
    , _fileapi(std::move(fileapi)) {}

void RotatingFileHandler::publish(const LogRecord &record) {
    lock_guard<mutex> lg(_mutex);
    stringstream buffer;
    getFormatter()->format(buffer, record);
    buffer << endl;
    if (shouldRollover(buffer)) {
        rollover();
    }
    _os << buffer.rdbuf() << flush;
}

namespace {

inline string getArchiveFilename(const std::string &filename, int i) {
    ostringstream oss;
    oss << filename << "." << i;
    return oss.str();
}

}  // namespace

void RotatingFileHandler::rollover() {
    _os.close();
    if (_backupCount > 0) {
        // backup old logfiles as agent.log.1 ... agent.log.<backupCount>
        for (auto i = static_cast<int>(_backupCount); i > 0; i--) {
            const string oldName =
                i > 1 ? getArchiveFilename(_filename, i - 1) : _filename;
            const string newName = getArchiveFilename(_filename, i);
            if (_fileapi->fileExists(oldName)) {
                if (_fileapi->fileExists(newName)) {
                    if (!_fileapi->remove(newName)) {
                        generic_error ge("Could not remove logfile " + newName);
                        Error(_logger) << ge;
                    }
                }
                if (!_fileapi->rename(oldName, newName)) {
                    generic_error ge("Could not rename " + oldName + " to " +
                                     newName);
                    Error(_logger) << ge;
                }
            }
        }
    } else {
        // no backup, just delete the old logfile...
        if (!_fileapi->remove(_filename)) {
            generic_error ge("Could not remove logfile " + _filename);
            Error(_logger) << ge;
        }
    }
    _os.open(_filename, ofstream::app);
}

bool RotatingFileHandler::shouldRollover(stringstream &buffer) {
    return _maxBytes > 0 &&
           static_cast<size_t>(_os.tellp() + buffer.tellp()) > _maxBytes;
}
