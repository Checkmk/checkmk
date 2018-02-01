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

#include "RotatingFileHandler.h"
#include <sys/stat.h>
#include <cstdio>

using std::endl;
using std::flush;
using std::lock_guard;
using std::mutex;
using std::ofstream;
using std::ostringstream;
using std::stringstream;
using std::string;

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
        for (int i = _backupCount; i > 0; i--) {
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
