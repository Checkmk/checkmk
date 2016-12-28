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
#include <unistd.h>
#include <cstdlib>
#include <memory>
#include <ostream>
#include <utility>
#include <vector>
#include "LogCache.h"
#include "LogEntry.h"
#include "Logger.h"
#include "Query.h"

#ifdef CMC
#include "cmc.h"
using std::to_string;
#endif

using std::make_unique;
using std::string;
using std::vector;

extern unsigned long g_max_lines_per_logfile;

Logfile::Logfile(Logger *logger, const CommandsHolder &commands_holder,
                 string path, bool watch)
    : _commands_holder(commands_holder)
    , _path(move(path))
    , _since(0)
    , _watch(watch)
    , _read_pos{}
    , _lineno(0)
#ifdef CMC
    , _world(nullptr)
#endif
    , _logger(logger)
    , _logclasses_read(0) {
    int fd = open(_path.c_str(), O_RDONLY);
    if (fd < 0) {
        generic_error ge("cannot open logfile " + _path);
        Informational(_logger) << ge;
        return;
    }

    char line[12];
    if (12 != read(fd, line, 12)) {
        close(fd);
        return;  // ignoring. might be empty
    }

    if (line[0] != '[' || line[11] != ']') {
        Informational(_logger) << "ignoring logfile '" << _path
                               << "': does not begin with '[123456789] '";
        close(fd);
        return;
    }

    line[11] = 0;
    _since = atoi(line + 1);
    close(fd);
}

Logfile::~Logfile() { flush(); }

void Logfile::flush() {
    for (auto &entry : _entries) {
        delete entry.second;
    }

    _entries.clear();
    _logclasses_read = 0;
}

void Logfile::load(LogCache *logcache, time_t since, time_t until,
                   unsigned logclasses) {
    // HIER KOENNTE ICH FLUSHEN, WENN g_active_world nicht mehr stimmt

    unsigned missing_types = logclasses & ~_logclasses_read;
    FILE *file = nullptr;
    // The current logfile has the _watch flag set to true.
    // In that case, if the logfile has grown, we need to
    // load the rest of the file, even if no logclasses
    // are missing.
    if (_watch) {
        file = fopen(_path.c_str(), "r");
        if (file == nullptr) {
            Informational(_logger) << "cannot open logfile '" << _path << "'";
            return;
        }
        // If we read this file for the first time, we initialize
        // the current file position to 0
        if (_lineno == 0) {
            fgetpos(file, &_read_pos);
        }

        // file might have grown. Read all classes that we already
        // have read to the end of the file
        if (_logclasses_read != 0u) {
            fsetpos(file, &_read_pos);  // continue at previous end
            loadRange(file, _logclasses_read, logcache, since, until,
                      logclasses);
            fgetpos(file, &_read_pos);
        }
        if (missing_types != 0u) {
            fseek(file, 0, SEEK_SET);
            _lineno = 0;
            loadRange(file, missing_types, logcache, since, until, logclasses);
            _logclasses_read |= missing_types;
            fgetpos(file, &_read_pos);  // remember current end of file
        }
        fclose(file);
    } else {
        if (missing_types == 0) {
            return;
        }

        file = fopen(_path.c_str(), "r");
        if (file == nullptr) {
            generic_error ge("cannot open logfile " + _path);
            Informational(_logger) << ge;
            return;
        }

        _lineno = 0;
        loadRange(file, missing_types, logcache, since, until, logclasses);
        fclose(file);
        _logclasses_read |= missing_types;
    }
}

void Logfile::loadRange(FILE *file, unsigned missing_types, LogCache *logcache,
                        time_t since, time_t until, unsigned logclasses) {
    vector<char> linebuffer(65536);
    while (fgets(&linebuffer[0], linebuffer.size(), file) != nullptr) {
        if (_lineno >= g_max_lines_per_logfile) {
            Error(_logger) << "more than " << g_max_lines_per_logfile
                           << " lines in " << this->_path
                           << ", ignoring the rest!";
            return;
        }
        _lineno++;
        if (processLogLine(_lineno, &linebuffer[0], missing_types)) {
            logcache->handleNewMessage(this, since, until,
                                       logclasses);  // memory management
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
        LogEntry *entry = it->second;
        if (((1u << static_cast<int>(entry->_logclass)) & logclasses) != 0u) {
            delete entry;
            _entries.erase(it++);
            freed++;
        } else {
            ++it;
        }
    }
    _logclasses_read &= ~logclasses;
    return freed;
}

bool Logfile::processLogLine(uint32_t lineno, const char *linebuffer,
                             unsigned logclasses) {
    auto entry = make_unique<LogEntry>(_commands_holder, lineno, linebuffer);
    // ignored invalid lines
    if (entry->_logclass == LogEntry::Class::invalid) {
        return false;
    }
    if (((1u << static_cast<int>(entry->_logclass)) & logclasses) == 0u) {
        return false;
    }
    uint64_t key = makeKey(entry->_time, entry->_lineno);
    if (_entries.find(key) != _entries.end()) {
        // this should never happen. The lineno must be unique!
        Error(_logger) << "strange duplicate logfile line " << entry->_complete;
        return false;
    }
    _entries.emplace(key, entry.release());
    return true;
}

logfile_entries_t *Logfile::getEntriesFromQuery(Query * /*unused*/,
                                                LogCache *logcache,
                                                time_t since, time_t until,
                                                unsigned logclasses) {
    updateReferences();  // Make sure existing references to objects point to
                         // correct world
    load(logcache, since, until,
         logclasses);  // make sure all messages are present
    return &_entries;
}

bool Logfile::answerQuery(Query *query, LogCache *logcache, time_t since,
                          time_t until, unsigned logclasses) {
    // Make sure existing references to objects point to correct world
    updateReferences();
    // make sure all messages are present
    load(logcache, since, until, logclasses);
    uint64_t sincekey = makeKey(since, 0);
    for (auto it = _entries.lower_bound(sincekey); it != _entries.end(); ++it) {
        LogEntry *entry = it->second;
        // end found or limit exceeded?
        if (entry->_time >= until || !query->processDataset(entry)) {
            return false;  // limit exceeded
        }
    }
    return true;
}

bool Logfile::answerQueryReverse(Query *query, LogCache *logcache, time_t since,
                                 time_t until, unsigned logclasses) {
    updateReferences();  // Make sure existing references to objects point to
                         // correct world
    load(logcache, since, until,
         logclasses);  // make sure all messages are present
    uint64_t untilkey = makeKey(until, 999999999);
    auto it = _entries.upper_bound(untilkey);
    while (it != _entries.begin()) {
        --it;
        LogEntry *entry = it->second;
        if (entry->_time < since) {
            return false;  // end found
        }
        if (!query->processDataset(entry)) {
            return false;  // limit exceeded
        }
    }
    return true;
}

uint64_t Logfile::makeKey(time_t t, unsigned lineno) {
    return (static_cast<uint64_t>(t) << 32) | static_cast<uint64_t>(lineno);
}

void Logfile::updateReferences() {
#ifdef CMC
    // If our references in cached log entries do not point to the currently
    // active configuration world, then update all references
    if (_world != g_live_world) {
        unsigned num = 0;
        for (auto &entry : _entries) {
            num += entry.second->updateReferences(_commands_holder);
        }
        Notice(_logger) << "updated " << num << " log cache references of "
                        << _path << " to new world.";
        _world = g_live_world;
    }
#endif
}

#ifdef CMC
// Read complete file into newly allocated buffer. Returns a pointer
// to a malloced buffer, that the caller must free (or 0, in case of
// an error). The buffer is 2 bytes larger then the file. One byte
// at the beginning and at the end of the buffer are '\0'.
char *Logfile::readIntoBuffer(size_t *size) {
    int fd = open(_path.c_str(), O_RDONLY);
    if (fd < 0) {
        generic_error ge("cannot open " + _path + " for reading");
        Warning(_logger) << ge;
        return nullptr;
    }

    off_t o = lseek(fd, 0, SEEK_END);
    if (o == -1) {
        generic_error ge("cannot seek to end of " + _path);
        Warning(_logger) << ge;
        close(fd);
        return nullptr;
    }

    *size = o;
    lseek(fd, 0, SEEK_SET);

    // add space for binary 0 at beginning and end
    char *buffer = static_cast<char *>(malloc(*size + 2));
    if (buffer == nullptr) {
        generic_error ge("cannot malloc buffer for reading " + _path);
        Warning(_logger) << ge;
        close(fd);
        return nullptr;
    }

    ssize_t r = read(fd, buffer + 1, *size);
    if (r < 0) {
        generic_error ge("cannot read " + to_string(*size) + " bytes from " +
                         _path);
        Warning(_logger) << ge;
        free(buffer);
        close(fd);
        return nullptr;
    }
    if (static_cast<size_t>(r) != *size) {
        Warning(_logger) << "read only " << r << " out of " << *size
                         << " bytes from " << _path;
        free(buffer);
        close(fd);
        return nullptr;
    }
    buffer[0] = 0;
    buffer[*size + 1] = 0;  // zero-terminate

    close(fd);
    return buffer;
}
#endif
