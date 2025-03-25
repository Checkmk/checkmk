// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/LogCache.h"

#include <iostream>
#include <optional>
#include <string>
#include <system_error>
#include <utility>

#include "livestatus/ChronoUtils.h"
#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/Logger.h"
#include "livestatus/Query.h"

namespace {
// Check memory every N'th new message
constexpr unsigned long check_mem_cycle = 1000;
}  // namespace

// Figure out the time interval for the query: In queries for the monitoring
// history, there should always be a time range in the form of one or two filter
// expressions for "time"". We use that to limit the number of log files we need
// to scan and to find the optimal entry point into the log file. Note that we
// use a half-open interval, but the bounds are inclusive, so we need to add 1
// to the LUB.
// static
LogPeriod LogPeriod ::make(const Query &query) {
    using sc = std::chrono::system_clock;
    auto now = sc::to_time_t(sc::now());
    return {
        .since =
            sc::from_time_t(query.greatestLowerBoundFor("time").value_or(0)),
        .until =
            sc::from_time_t(query.leastUpperBoundFor("time").value_or(now) + 1),
    };
}

std::ostream &operator<<(std::ostream &os, const LogPeriod &p) {
    return os << "[" << FormattedTimePoint(p.since) << ", "
              << FormattedTimePoint(p.until) << ")";
}

LogCache::LogCache(ICore *core)
    : core_{core}, num_cached_log_messages_{0}, num_at_last_check_{0} {}

void LogCache::update() {
    if (!log_files_.empty() &&
        core_->last_logfile_rotation() <= last_index_update_) {
        return;
    }

    Informational{logger()} << "updating log file index";

    log_files_.clear();
    num_cached_log_messages_ = 0;

    last_index_update_ = std::chrono::system_clock::now();
    // We need to find all relevant log files. This includes directory, the
    // current nagios.log and all files in the archive.
    const auto paths = core_->paths();
    addToIndex(paths->history_file(), true);

    const std::filesystem::path dirpath = paths->history_archive_directory();
    try {
        for (const auto &entry : std::filesystem::directory_iterator(dirpath)) {
            addToIndex(entry.path(), false);
        }
    } catch (const std::filesystem::filesystem_error &e) {
        if (e.code() != std::errc::no_such_file_or_directory) {
            Warning{logger()} << "updating log file index: " << e.what();
        }
    }

    if (log_files_.empty()) {
        Notice{logger()} << "no log file found, not even "
                         << paths->history_file();
    }
}

void LogCache::addToIndex(const std::filesystem::path &path, bool watch) {
    try {
        auto log_file = std::make_unique<Logfile>(logger(), this, path, watch);
        auto since = log_file->since();
        if (!log_files_.emplace(since, std::move(log_file)).second) {
            // Complain if an entry with that 'since' already exists. Under
            // normal circumstances this never happens, but the user might have
            // copied files around by hand.
            Warning{logger()} << "ignoring duplicate log file " << path;
        }
    } catch (generic_error &e) {
        Warning{logger()} << e;
        return;
    }
}

// This method is called each time a log message is loaded into memory. If the
// number of messages loaded in memory is too large, memory will be freed by
// flushing log files and message not needed by the current query.
//
// The parameters to this method reflect the current query, not the messages
// that have just been loaded.
void LogCache::logLineHasBeenAdded(Logfile *log_file,
                                   LogEntryClasses log_entry_classes_to_keep) {
    const unsigned log_classes =
        log_entry_classes_to_keep.to_ulong();  // TODO(sp)
    if (++num_cached_log_messages_ <= core_->maxCachedMessages()) {
        return;  // current message count still allowed, everything ok
    }

    // Memory checking and freeing consumes CPU resources. We save resources by
    // avoiding the memory check each time a new message is loaded when being in
    // a sitation where no memory can be freed. We do this by suppressing the
    // check when the number of messages loaded into memory has not grown by at
    // least check_mem_cycle messages.
    if (num_cached_log_messages_ < num_at_last_check_ + check_mem_cycle) {
        return;  // Do not check this time
    }

    // [1] Delete old log files: Begin deleting with the oldest log file
    // available
    auto it{log_files_.begin()};
    for (; it != log_files_.end(); ++it) {
        if (it->second.get() == log_file) {
            break;  // Do not touch the log file the Query is currently
                    // accessing
        }
        if (it->second->size() > 0) {
            num_cached_log_messages_ -= it->second->freeMessages(~0);
            if (num_cached_log_messages_ <= core_->maxCachedMessages()) {
                num_at_last_check_ = num_cached_log_messages_;
                return;
            }
        }
    }
    // The end of this loop must be reached by 'break'. At least one log file
    // must be the current log file. So now 'it' points to the current log file.
    // We save that pointer for later.
    auto queryit = it;

    // [2] Delete message classes irrelevent to current query: Starting from the
    // current log file (we broke out of the previous loop just when 'it'
    // pointed to that)
    for (; it != log_files_.end(); ++it) {
        if (it->second->size() > 0 &&
            (it->second->classesRead() & ~log_classes) != 0) {
            Debug{logger()} << "freeing classes " << ~log_classes << " of file "
                            << it->second->path();
            num_cached_log_messages_ -= it->second->freeMessages(~log_classes);
            if (num_cached_log_messages_ <= core_->maxCachedMessages()) {
                num_at_last_check_ = num_cached_log_messages_;
                return;
            }
        }
    }

    // [3] Flush newest log files: If there are still too many messages loaded,
    // continue flushing log files from the oldest to the newest starting at the
    // file just after (i.e. newer than) the current log file
    for (it = ++queryit; it != log_files_.end(); ++it) {
        if (it->second->size() > 0) {
            Debug{logger()} << "flush newer log, " << it->second->size()
                            << " number of entries";
            num_cached_log_messages_ -= it->second->freeMessages(~0);
            if (num_cached_log_messages_ <= core_->maxCachedMessages()) {
                num_at_last_check_ = num_cached_log_messages_;
                return;
            }
        }
    }
    // If we reach this point, no more log files can be unloaded, despite the
    // fact that there are still too many messages loaded.
    num_at_last_check_ = num_cached_log_messages_;
    Debug{logger()} << "cannot unload more messages, still "
                    << num_cached_log_messages_ << " loaded (max is "
                    << core_->maxCachedMessages() << ")";
}

Logger *LogCache::logger() const { return core_->loggerLivestatus(); }
