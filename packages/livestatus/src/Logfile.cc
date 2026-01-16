// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/Logfile.h"

#include <fcntl.h>

#include <cerrno>
#include <chrono>
#include <fstream>
#include <ranges>
#include <stdexcept>
#include <vector>

#include "livestatus/ChronoUtils.h"
#include "livestatus/LogCache.h"
#include "livestatus/Logger.h"

namespace {
std::chrono::system_clock::time_point firstTimestampOf(
    const std::filesystem::path &path) {
    std::string line;
    if (std::ifstream is{path}; is && std::getline(is, line)) {
        try {
            return LogEntry{{}, line}.time();
        } catch (const std::invalid_argument &) {
            errno = EINVAL;
        }
    }
    throw generic_error{"cannot determine first timestamp of " + path.string()};
}
}  // namespace

Logfile::Logfile(Logger *logger, LogCache *log_cache,
                 std::filesystem::path path, bool watch)
    : _logger(logger)
    , _log_cache(log_cache)
    , _path(std::move(path))
    , _since(firstTimestampOf(_path))
    , _watch(watch)
    , _read_pos{}
    , _lineno(0)
    , _logclasses_read(0) {}

std::ostream &operator<<(std::ostream &os, const Logfile &f) {
    return os << "log file " << f.path() << " (starts at timestamp "
              << std::chrono::system_clock::to_time_t(f.since()) << " = "
              << FormattedTimePoint(f.since()) << ")";
}

void Logfile::load(const LogRestrictions &restrictions,
                   size_t max_cached_messages) {
    const unsigned missing_types = restrictions.log_entry_classes.to_ulong() &
                                   ~_logclasses_read;  // TODO(sp)
    // The current logfile has the _watch flag set to true.
    // In that case, if the logfile has grown, we need to
    // load the rest of the file, even if no logclasses
    // are missing.
    // TODO(sp) Check return values of fclose, fgetpos, fsetpos, fseek.
    if (_watch) {
        // NOLINTNEXTLINE(cppcoreguidelines-owning-memory)
        FILE *file = fopen(_path.c_str(), "r");
        if (file == nullptr) {
            const generic_error ge("cannot open logfile " + _path.string());
            Informational(_logger) << ge;
            return;
        }
        // If we read this file for the first time, we initialize
        // the current file position to 0
        if (_lineno == 0) {
            (void)fgetpos(file, &_read_pos);
        }

        // file might have grown. Read all classes that we already
        // have read to the end of the file
        if (_logclasses_read != 0U) {
            (void)fsetpos(file, &_read_pos);  // continue at previous end
            loadRange(restrictions, file, _logclasses_read,
                      max_cached_messages);
            if (::ferror(file) == 0) {
                (void)fgetpos(file, &_read_pos);
            }
        }
        if (missing_types != 0U) {
            (void)fseek(file, 0, SEEK_SET);
            _lineno = 0;
            loadRange(restrictions, file, missing_types, max_cached_messages);
            _logclasses_read |= missing_types;
            if (::ferror(file) == 0) {
                (void)fgetpos(file, &_read_pos);
            }
        }
        // NOLINTNEXTLINE(cppcoreguidelines-owning-memory)
        (void)fclose(file);
    } else {
        if (missing_types == 0) {
            return;
        }

        // NOLINTNEXTLINE(cppcoreguidelines-owning-memory)
        FILE *file = fopen(_path.c_str(), "r");
        if (file == nullptr) {
            const generic_error ge("cannot open logfile " + _path.string());
            Informational(_logger) << ge;
            return;
        }

        _lineno = 0;
        loadRange(restrictions, file, missing_types, max_cached_messages);
        _logclasses_read |= missing_types;
        // NOLINTNEXTLINE(cppcoreguidelines-owning-memory)
        (void)fclose(file);
    }
}

void Logfile::loadRange(const LogRestrictions &restrictions, FILE *file,
                        unsigned missing_types, size_t max_cached_messages) {
    std::vector<char> linebuffer(65536);
    // TODO(sp) We should really use C++ I/O here...
    while (fgets(linebuffer.data(), static_cast<int>(linebuffer.size()),
                 file) != nullptr) {
        if (_lineno >= restrictions.max_lines_per_log_file) {
            Error(_logger) << "more than "
                           << restrictions.max_lines_per_log_file
                           << " lines in " << _path << ", ignoring the rest!";
            return;
        }
        _lineno++;
        // remove trailing newline (should be nuked, see above)
        auto it = std::ranges::find_if(
            linebuffer, [](auto ch) { return ch == '\0' || ch == '\n'; });
        if (it != linebuffer.end()) {
            *it = '\0';
        }
        if (processLogLine(_lineno, linebuffer.data(), missing_types)) {
            _log_cache->logLineHasBeenAdded(
                this, restrictions.log_entry_classes, max_cached_messages);
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
        if (((1U << static_cast<int>(it->second->log_class())) & logclasses) !=
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
    std::unique_ptr<LogEntry> entry;
    try {
        entry = std::make_unique<LogEntry>(lineno, std::move(line));
    } catch (const std::invalid_argument &) {
        return false;  // simply ignore invalid lines
    }
    if (((1U << static_cast<int>(entry->log_class())) & logclasses) == 0U) {
        return false;
    }
    auto key = makeKey(entry->time(), entry->lineno());
    if (_entries.contains(key)) {
        // this should never happen. The lineno must be unique!
        Error(_logger) << "strange duplicate logfile line " << entry->message();
        return false;
    }
    _entries[key] = std::move(entry);
    return true;
}

const Logfile::map_type *Logfile::getEntriesFor(
    const LogRestrictions &restrictions, size_t max_cached_messages) {
    // make sure all messages are present
    load(restrictions, max_cached_messages);
    return &_entries;
}
