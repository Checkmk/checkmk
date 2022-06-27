
#include "stdafx.h"

#include "eventlogbase.h"

#include "eventlogstd.h"
#include "eventlogvista.h"
#include "logger.h"

namespace cma::evl {
std::unique_ptr<EventLogBase> OpenEvl(const std::wstring &name,
                                      bool vista_api) {
    if (vista_api && g_evt.close != nullptr) {
        return std::make_unique<EventLogVista>(name);
    }

    return std::make_unique<EventLog>(name);
}

/// scans whole eventlog to find worst possible case
///
/// returns pos and case
std::pair<uint64_t, cma::cfg::EventLevels> ScanEventLog(
    EventLogBase &log, uint64_t pos, cma::cfg::EventLevels level) {
    // we must seek past the previously read event - if there was one
    log.seek(choosePos(pos));

    auto worst_state = cma::cfg::EventLevels::kAll;
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
bool operator!=(const EventLogRecordBase::ptr &lhs,
                const EventLogRecordBase::ptr &rhs) {
    return !(lhs == rhs);
}
}  // namespace

/// scans eventlog and applies processor to every entry.
///
/// returns last scanned pos where processor returns false
uint64_t PrintEventLog(EventLogBase &log, uint64_t from_pos,
                       cma::cfg::EventLevels level, bool hide_context,
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
            auto str = record->stringize(level, hide_context);
            if (!str.empty() && !processor(str)) {
                // processor request to stop scanning
                break;
            }
            previous = std::move(record);
        } else {
            auto str = record->stringize(level, hide_context);
            if (!str.empty() && !processor(str)) {
                // processor request to stop scanning
                break;
            }
        }
    }

    return last_pos;
}

}  // namespace cma::evl
