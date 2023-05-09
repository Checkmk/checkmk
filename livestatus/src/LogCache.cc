// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "LogCache.h"

#include <filesystem>
#include <sstream>
#include <string>
#include <utility>

#include "Logfile.h"
#include "Logger.h"
#include "MonitoringCore.h"

namespace {
// Check memory every N'th new message
constexpr unsigned long check_mem_cycle = 1000;
}  // namespace

LogCache::LogCache(MonitoringCore *mc)
    : _mc(mc), _num_cached_log_messages(0), _num_at_last_check(0) {}

void LogCache::update() {
    if (!_logfiles.empty() &&
        _mc->last_logfile_rotation() <= _last_index_update) {
        return;
    }

    Informational(logger()) << "updating log file index";

    _logfiles.clear();
    _num_cached_log_messages = 0;

    _last_index_update = std::chrono::system_clock::now();
    // We need to find all relevant logfiles. This includes directory, the
    // current nagios.log and all files in the archive.
    addToIndex(std::make_unique<Logfile>(logger(), this, _mc->historyFilePath(),
                                         true));

    std::filesystem::path dirpath = _mc->logArchivePath();
    try {
        for (const auto &entry : std::filesystem::directory_iterator(dirpath)) {
            addToIndex(
                std::make_unique<Logfile>(logger(), this, entry.path(), false));
        }
    } catch (const std::filesystem::filesystem_error &e) {
        Warning(logger()) << "updating log file index: " << e.what();
    }

    if (_logfiles.empty()) {
        Notice(logger()) << "no log file found, not even "
                         << _mc->historyFilePath();
    }
}

void LogCache::addToIndex(std::unique_ptr<Logfile> logfile) {
    time_t since = logfile->since();
    if (since == 0) {
        return;
    }
    // make sure that no entry with that 'since' is existing yet.  Under normal
    // circumstances this never happens, but the user might have copied files
    // around.
    if (_logfiles.find(since) != _logfiles.end()) {
        Warning(logger()) << "ignoring duplicate log file " << logfile->path();
        return;
    }

    _logfiles.emplace(since, std::move(logfile));
}

// This method is called each time a log message is loaded into memory. If the
// number of messages loaded in memory is too large, memory will be freed by
// flushing logfiles and message not needed by the current query.
//
// The parameters to this method reflect the current query, not the messages
// that have just been loaded.
void LogCache::logLineHasBeenAdded(Logfile *logfile, unsigned logclasses) {
    if (++_num_cached_log_messages <= _mc->maxCachedMessages()) {
        return;  // current message count still allowed, everything ok
    }

    // Memory checking and freeing consumes CPU resources. We save resources by
    // avoiding the memory check each time a new message is loaded when being in
    // a sitation where no memory can be freed. We do this by suppressing the
    // check when the number of messages loaded into memory has not grown by at
    // least check_mem_cycle messages.
    if (_num_cached_log_messages < _num_at_last_check + check_mem_cycle) {
        return;  // Do not check this time
    }

    // [1] Delete old logfiles: Begin deleting with the oldest logfile available
    logfiles_t::iterator it;
    for (it = _logfiles.begin(); it != _logfiles.end(); ++it) {
        if (it->second.get() == logfile) {
            break;  // Do not touch the logfile the Query is currently accessing
        }
        if (it->second->size() > 0) {
            _num_cached_log_messages -= it->second->freeMessages(~0);
            if (_num_cached_log_messages <= _mc->maxCachedMessages()) {
                _num_at_last_check = _num_cached_log_messages;
                return;
            }
        }
    }
    // The end of this loop must be reached by 'break'. At least one logfile
    // must be the current logfile. So now 'it' points to the current logfile.
    // We save that pointer for later.
    auto queryit = it;

    // [2] Delete message classes irrelevent to current query: Starting from the
    // current logfile (we broke out of the previous loop just when 'it' pointed
    // to that)
    for (; it != _logfiles.end(); ++it) {
        if (it->second->size() > 0 &&
            (it->second->classesRead() & ~logclasses) != 0) {
            Debug(logger()) << "freeing classes " << ~logclasses << " of file "
                            << it->second->path();
            _num_cached_log_messages -= it->second->freeMessages(~logclasses);
            if (_num_cached_log_messages <= _mc->maxCachedMessages()) {
                _num_at_last_check = _num_cached_log_messages;
                return;
            }
        }
    }

    // [3] Flush newest logfiles: If there are still too many messages loaded,
    // continue flushing logfiles from the oldest to the newest starting at the
    // file just after (i.e. newer than) the current logfile
    for (it = ++queryit; it != _logfiles.end(); ++it) {
        if (it->second->size() > 0) {
            Debug(logger()) << "flush newer log, " << it->second->size()
                            << " number of entries";
            _num_cached_log_messages -= it->second->freeMessages(~0);
            if (_num_cached_log_messages <= _mc->maxCachedMessages()) {
                _num_at_last_check = _num_cached_log_messages;
                return;
            }
        }
    }
    // If we reach this point, no more logfiles can be unloaded, despite the
    // fact that there are still too many messages loaded.
    _num_at_last_check = _num_cached_log_messages;
    Debug(logger()) << "cannot unload more messages, still "
                    << _num_cached_log_messages << " loaded (max is "
                    << _mc->maxCachedMessages() << ")";
}

size_t LogCache::numCachedLogMessages() const {
    return _num_cached_log_messages;
}

Logger *LogCache::logger() const { return _mc->loggerLivestatus(); }
