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

// https://github.com/include-what-you-use/include-what-you-use/issues/166
// IWYU pragma: no_include <ext/alloc_traits.h>
#include "Logfile.h"
#include <fcntl.h>
#include <cstdlib>
#include <sstream>
#include <utility>
#include <vector>
#include "LogCache.h"
#include "LogEntry.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"

#ifdef CMC
#include "cmc.h"
#endif

namespace {
time_t firstTimestampOf(const fs::path &path, Logger *logger) {
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

Logfile::Logfile(MonitoringCore *mc, LogCache *logcache, fs::path path,
                 bool watch)
    : _mc(mc)
    , _logcache(logcache)
    , _path(std::move(path))
    , _since(firstTimestampOf(_path, logger()))
    , _watch(watch)
    , _read_pos{}
    , _lineno(0)
#ifdef CMC
    , _world(nullptr)
#endif
    , _logclasses_read(0) {
}

void Logfile::flush() {
    _entries.clear();
    _logclasses_read = 0;
}

void Logfile::load(unsigned logclasses) {
    unsigned missing_types = logclasses & ~_logclasses_read;
    // The current logfile has the _watch flag set to true.
    // In that case, if the logfile has grown, we need to
    // load the rest of the file, even if no logclasses
    // are missing.
    if (_watch) {
        FILE *file = fopen(_path.c_str(), "r");
        if (file == nullptr) {
            generic_error ge("cannot open logfile " + _path.string());
            Informational(logger()) << ge;
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
            loadRange(file, _logclasses_read, logclasses);
            fgetpos(file, &_read_pos);
        }
        if (missing_types != 0U) {
            fseek(file, 0, SEEK_SET);
            _lineno = 0;
            loadRange(file, missing_types, logclasses);
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
            Informational(logger()) << ge;
            return;
        }

        _lineno = 0;
        loadRange(file, missing_types, logclasses);
        _logclasses_read |= missing_types;
        fclose(file);
    }
}

void Logfile::loadRange(FILE *file, unsigned missing_types,
                        unsigned logclasses) {
    std::vector<char> linebuffer(65536);
    // TODO(sp) We should really use C++ I/O here...
    while (fgets(&linebuffer[0], static_cast<int>(linebuffer.size()), file) !=
           nullptr) {
        if (_lineno >= _mc->maxLinesPerLogFile()) {
            Error(logger()) << "more than " << _mc->maxLinesPerLogFile()
                            << " lines in " << _path << ", ignoring the rest!";
            return;
        }
        _lineno++;
        // remove trailing newline (should be nuked, see above)
        for (auto &ch : linebuffer) {
            if (ch == '\0' || ch == '\n') {
                ch = '\0';
                break;
            }
        }
        if (processLogLine(_lineno, &linebuffer[0], missing_types)) {
            _logcache->logLineHasBeenAdded(this, logclasses);
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
        if (((1U << static_cast<int>(it->second->_logclass)) & logclasses) !=
            0U) {
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
    auto entry = std::make_unique<LogEntry>(_mc, lineno, std::move(line));
    // ignored invalid lines
    if (entry->_logclass == LogEntry::Class::invalid) {
        return false;
    }
    if (((1U << static_cast<int>(entry->_logclass)) & logclasses) == 0U) {
        return false;
    }
    uint64_t key = makeKey(entry->_time, entry->_lineno);
    if (_entries.find(key) != _entries.end()) {
        // this should never happen. The lineno must be unique!
        Error(logger()) << "strange duplicate logfile line "
                        << entry->_complete;
        return false;
    }
    _entries[key] = std::move(entry);
    return true;
}

const logfile_entries_t *Logfile::getEntriesFor(unsigned logclasses) {
    // Make sure existing references to objects point to correct world
    updateReferences();
    // make sure all messages are present
    load(logclasses);
    return &_entries;
}

bool Logfile::answerQueryReverse(Query *query, time_t since, time_t until,
                                 unsigned logclasses) {
    auto entries = getEntriesFor(logclasses);
    // TODO(sp) Move the stuff below out of this class. Tricky part: makeKey
    auto it = entries->upper_bound(makeKey(until, 999999999));
    while (it != entries->begin()) {
        --it;
        // end found or limit exceeded?
        if (it->second->_time < since ||
            !query->processDataset(Row(it->second.get()))) {
            return false;
        }
    }
    return true;
}

uint64_t Logfile::makeKey(time_t t, size_t lineno) {
    return (static_cast<uint64_t>(t) << 32) | static_cast<uint64_t>(lineno);
}

void Logfile::updateReferences() {
#ifdef CMC
    // If our references in cached log entries do not point to the currently
    // active configuration world, then update all references
    if (_world != g_live_world) {
        unsigned num = 0;
        for (auto &entry : _entries) {
            num += entry.second->updateReferences(_mc);
        }
        Notice(logger()) << "updated " << num << " log cache references of "
                         << _path << " to new world.";
        _world = g_live_world;
    }
#endif
}

Logger *Logfile::logger() const { return _mc->loggerLivestatus(); }
