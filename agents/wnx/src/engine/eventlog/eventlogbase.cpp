
#include "stdafx.h"

#include "eventlog/eventlogbase.h"

#include <fmt/core.h>

#include "eventlog/eventlogstd.h"
#include "eventlog/eventlogvista.h"
#include "wnx/logger.h"

namespace cma::evl {
std::unique_ptr<EventLogBase> OpenEvl(const std::wstring &name,
                                      bool vista_api) {
    if (vista_api && IsEvtApiAvailable()) {
        return std::make_unique<EventLogVista>(name);
    }

    return std::make_unique<EventLog>(name);
}

/// scans whole eventlog to find worst possible case
///
/// returns pos and case
std::pair<uint64_t, cfg::EventLevels> ScanEventLog(EventLogBase &log,
                                                   uint64_t pos,
                                                   cfg::EventLevels level) {
    // we must seek past the previously read event - if there was one
    log.seek(choosePos(pos));

    auto worst_state = cfg::EventLevels::kAll;
    auto last_pos = pos;

    while (true) {
        EventLogRecordBase::ptr record{log.readRecord()};

        if (!record) {
            break;
        }

        last_pos = record->recordId();
        auto calculated = record->calcEventLevel();
        worst_state = std::max(worst_state, calculated);
    }

    return {last_pos, worst_state};
}

namespace {
bool operator==(const EventLogRecordBase::ptr &lhs,
                const EventLogRecordBase::ptr &rhs) {
    if (lhs == nullptr && rhs == nullptr) {
        return true;
    }

    if (lhs != nullptr && rhs != nullptr) {
        return lhs->eventLevel() == rhs->eventLevel() &&
               lhs->eventId() == rhs->eventId() &&
               lhs->eventQualifiers() == rhs->eventQualifiers() &&
               lhs->source() == rhs->source() &&
               lhs->makeMessage() == rhs->makeMessage();
    }

    return false;
}

}  // namespace

/// scans eventlog and applies processor to every entry.
///
/// returns last scanned pos where processor returns false
uint64_t PrintEventLog(EventLogBase &log, uint64_t from_pos,
                       cfg::EventLevels level, cfg::EventContext context,
                       SkipDuplicatedRecords skip,
                       const EvlProcessor &processor) {
    // we must seek past the previously read event - if there was one
    log.seek(choosePos(from_pos));

    auto last_pos = from_pos;

    EventLogRecordBase::ptr previous;
    size_t duplicated_count = 0;
    while (true) {
        EventLogRecordBase::ptr record{log.readRecord()};
        if (!record) {
            if (skip == SkipDuplicatedRecords::yes && duplicated_count) {
                processor(fmt::format(kSkippedMessageFormat, duplicated_count));
            }
            break;
        }

        last_pos = record->recordId();
        if (skip == SkipDuplicatedRecords::yes) {
            if (previous == record) {
                ++duplicated_count;
                continue;
            }
            if (duplicated_count) {
                processor(fmt::format(kSkippedMessageFormat, duplicated_count));
                duplicated_count = 0;
            }
            auto str = record->stringize(level, context);
            if (!str.empty() && !processor(str)) {
                // processor request to stop scanning
                break;
            }
            previous = std::move(record);
        } else {
            auto str = record->stringize(level, context);
            if (!str.empty() && !processor(str)) {
                // processor request to stop scanning
                break;
            }
        }
    }

    return last_pos;
}

std::string EventLogRecordBase::stringize(cfg::EventLevels required,
                                          cfg::EventContext context) const {
    // convert UNIX timestamp to local time
    auto ch = getEventSymbol(required);
    if (context == cfg::EventContext::hide && ch == '.') {
        return {};
    }

    auto time_generated = timeGenerated();
    const auto *t = ::localtime(&time_generated);  // NOLINT
    char timestamp[64];
    ::strftime(timestamp, sizeof timestamp, "%b %d %H:%M:%S", t);

    // source is the application that produced the event
    std::string source_name = wtools::ToUtf8(source());
    std::ranges::replace(source_name, ' ', '_');

    return fmt::format("{} {} {}.{} {} {}\n",
                       ch,                 // char symbol
                       timestamp,          //
                       eventQualifiers(),  //
                       eventId(),          //
                       source_name,        //
                       wtools::ToUtf8(makeMessage()));
}

char EventLogRecordBase::getEventSymbol(cfg::EventLevels required) const {
    switch (eventLevel()) {
        case Level::error:
            return 'C';
        case Level::warning:
            return 'W';
        case Level::information:
        case Level::audit_success:
        case Level::success:
            return required == cfg::EventLevels::kAll
                       ? 'O'
                       : '.';  // potential drop of context
        case Level::audit_failure:
            return 'C';
    }
    // unreachable
    return ' ';
}

/// decode windows level to universal
cfg::EventLevels EventLogRecordBase::calcEventLevel() const {
    switch (eventLevel()) {
        case Level::error:
            return cfg::EventLevels::kCrit;
        case Level::warning:
            return cfg::EventLevels::kWarn;
        case Level::information:
        case Level::audit_success:
        case Level::success:
            return cfg::EventLevels::kAll;
        case Level::audit_failure:
            return cfg::EventLevels::kCrit;
    }
    // unreachable
    return cfg::EventLevels::kCrit;
}

}  // namespace cma::evl
