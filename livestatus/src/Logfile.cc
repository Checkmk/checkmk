// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "Logfile.h"
#include <fcntl.h>
#include <algorithm>
#include <cstdlib>
#include <sstream>
#include <utility>
#include <vector>
#include "LogCache.h"
#include "LogEntry.h"
#include "Logger.h"

namespace {
time_t firstTimestampOf(const std::filesystem::path &path, Logger *logger) {
    std::ifstream is(path, std::ios::binary);
    if (!is) {
        generic_error ge("cannot open logfile " + path.string());
        Informational(logger) << ge;
        return 0;
    }

    char line[12];
    is.read(line, sizeof(line));
    if (!is) {
        return 0;  // ignoring. might be empty
    }

    if (line[0] != '[' || line[11] != ']') {
        Informational(logger) << "ignoring logfile '" << path
                              << "': does not begin with '[123456789] '";
        return 0;
    }

    line[11] = 0;
    return atoi(line + 1);
}
}  // namespace

Logfile::Logfile(Logger *logger, LogCache *log_cache,
                 std::filesystem::path path, bool watch)
    : _logger(logger)
    , _log_cache(log_cache)
    , _path(std::move(path))
    , _since(firstTimestampOf(_path, _logger))
    , _watch(watch)
    , _read_pos{}
    , _lineno(0)
    , _logclasses_read(0) {}

void Logfile::load(size_t max_lines_per_logfile, unsigned logclasses) {
    unsigned missing_types = logclasses & ~_logclasses_read;
    // The current logfile has the _watch flag set to true.
    // In that case, if the logfile has grown, we need to
    // load the rest of the file, even if no logclasses
    // are missing.
    if (_watch) {
        FILE *file = fopen(_path.c_str(), "r");
        if (file == nullptr) {
            generic_error ge("cannot open logfile " + _path.string());
            Informational(_logger) << ge;
            return;
        }
        // If we read this file for the first time, we initialize
        // the current file position to 0
        if (_lineno == 0) {
            fgetpos(file, &_read_pos);
        }

        // file might have grown. Read all classes that we already
        // have read to the end of the file
        if (_logclasses_read != 0U) {
            fsetpos(file, &_read_pos);  // continue at previous end
            loadRange(max_lines_per_logfile, file, _logclasses_read,
                      logclasses);
            fgetpos(file, &_read_pos);
        }
        if (missing_types != 0U) {
            fseek(file, 0, SEEK_SET);
            _lineno = 0;
            loadRange(max_lines_per_logfile, file, missing_types, logclasses);
            _logclasses_read |= missing_types;
            fgetpos(file, &_read_pos);  // remember current end of file
        }
        fclose(file);
    } else {
        if (missing_types == 0) {
            return;
        }

        FILE *file = fopen(_path.c_str(), "r");
        if (file == nullptr) {
            generic_error ge("cannot open logfile " + _path.string());
            Informational(_logger) << ge;
            return;
        }

        _lineno = 0;
        loadRange(max_lines_per_logfile, file, missing_types, logclasses);
        _logclasses_read |= missing_types;
        fclose(file);
    }
}

void Logfile::loadRange(size_t max_lines_per_logfile, FILE *file,
                        unsigned missing_types, unsigned logclasses) {
    std::vector<char> linebuffer(65536);
    // TODO(sp) We should really use C++ I/O here...
    while (fgets(&linebuffer[0], static_cast<int>(linebuffer.size()), file) !=
           nullptr) {
        if (_lineno >= max_lines_per_logfile) {
            Error(_logger) << "more than " << max_lines_per_logfile
                           << " lines in " << _path << ", ignoring the rest!";
            return;
        }
        _lineno++;
        // remove trailing newline (should be nuked, see above)
        auto it =
            std::find_if(linebuffer.begin(), linebuffer.end(),
                         [](auto ch) { return ch == '\0' || ch == '\n'; });
        if (it != linebuffer.end()) {
            *it = '\0';
        }
        if (processLogLine(_lineno, &linebuffer[0], missing_types)) {
            _log_cache->logLineHasBeenAdded(this, logclasses);
        }
    }
}

long Logfile::freeMessages(unsigned logclasses) {
    long freed = 0;
    // We have to be careful here: Erasing an element from an associative
    // container invalidates the iterator pointing to it. The solution is the
    // usual post-increment idiom, see Scott Meyers' "Effective STL", item 9
    // ("Choose carefully among erasing options.").
    for (auto it = _entries.begin(); it != _entries.end();) {
        if (((1U << static_cast<int>(it->second->_class)) & logclasses) != 0U) {
            _entries.erase(it++);
            freed++;
        } else {
            ++it;
        }
    }
    _logclasses_read &= ~logclasses;
    return freed;
}

bool Logfile::processLogLine(size_t lineno, std::string line,
                             unsigned logclasses) {
    auto entry = std::make_unique<LogEntry>(lineno, std::move(line));
    // ignored invalid lines
    if (entry->_class == LogEntry::Class::invalid) {
        return false;
    }
    if (((1U << static_cast<int>(entry->_class)) & logclasses) == 0U) {
        return false;
    }
    uint64_t key = makeKey(entry->_time, entry->_lineno);
    if (_entries.find(key) != _entries.end()) {
        // this should never happen. The lineno must be unique!
        Error(_logger) << "strange duplicate logfile line " << entry->_message;
        return false;
    }
    _entries[key] = std::move(entry);
    return true;
}

const logfile_entries_t *Logfile::getEntriesFor(size_t max_lines_per_logfile,
                                                unsigned logclasses) {
    // make sure all messages are present
    load(max_lines_per_logfile, logclasses);
    return &_entries;
}

// static
uint64_t Logfile::makeKey(time_t t, size_t lineno) {
    return (static_cast<uint64_t>(t) << 32) | static_cast<uint64_t>(lineno);
}
