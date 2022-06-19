// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef EventLogBase_h
#define EventLogBase_h

#include <fmt/format.h>

#include <ctime>
#include <functional>
#include <memory>
#include <ranges>
#include <string>

#include "common/cfg_info.h"
#include "common/wtools.h"

namespace cma::evl {
enum class SkipDuplicatedRecords { no, yes };
constexpr std::string_view kSkippedMessageFormat =
    "[the above message was repeated {} times]\n";
class EventLogRecordBase {
public:
    using ptr = std::unique_ptr<EventLogRecordBase>;
    enum class Level {
        error,
        warning,
        information,
        audit_failure,
        audit_success,
        success
    };

    EventLogRecordBase() = default;
    virtual ~EventLogRecordBase() = default;
    EventLogRecordBase(const EventLogRecordBase &) = delete;
    EventLogRecordBase &operator=(const EventLogRecordBase &) = delete;

    [[nodiscard]] virtual uint64_t recordId() const = 0;
    [[nodiscard]] virtual uint16_t eventId() const = 0;
    [[nodiscard]] virtual uint16_t eventQualifiers() const = 0;
    [[nodiscard]] virtual time_t timeGenerated() const = 0;
    [[nodiscard]] virtual std::wstring source() const = 0;
    [[nodiscard]] virtual Level eventLevel() const = 0;
    [[nodiscard]] virtual std::wstring makeMessage() const = 0;

    [[nodiscard]] std::string stringize(cfg::EventLevels required,
                                        bool hide_trash) const {
        // convert UNIX timestamp to local time
        auto ch = getEventSymbol(required);
        if (hide_trash && ch == '.') {
            return {};
        }

        auto time_generated = timeGenerated();
        const auto *t = ::localtime(&time_generated);
        char timestamp[64];
        ::strftime(timestamp, sizeof(timestamp), "%b %d %H:%M:%S", t);

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

    // for output in port
    [[nodiscard]] char getEventSymbol(cfg::EventLevels required) const {
        switch (eventLevel()) {
            case Level::error:
                return 'C';
            case Level::warning:
                return 'W';
            case Level::information:
            case Level::audit_success:
            case Level::success:
                return (required == cfg::EventLevels::kAll)
                           ? 'O'
                           : '.';  // potential drop of context
            case Level::audit_failure:
                return 'C';
            default:
                return 'u';
        }
    }

    // decode windows level to universal
    [[nodiscard]] cfg::EventLevels calcEventLevel() const {
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
            default:
                return cfg::EventLevels::kWarn;
        }
    }
};

class EventLogBase {
public:
    EventLogBase() = default;
    virtual ~EventLogBase() = default;
    EventLogBase(const EventLogBase &) = delete;
    EventLogBase &operator=(const EventLogBase &) = delete;

    /**
     * return the name/path of the eventlog monitored
     **/
    [[nodiscard]] virtual std::wstring getName() const = 0;

    /**
     * seek to the specified record on the next read or, if the record_number is
     * older than the oldest existing record, seek to the beginning. If the
     * record_number is the highest representable uint32_t, seek to the end of
     * the log such that only future events are retrieved
     *
     * WARNING:
     * The implementations for pre-Vista and post-Vista are completely
     * different.
     * We *must not* return any value as it is different between pre/post Vista.
     * For obtaining the ID of the last record in eventlog, please use
     * getLastRecordId instead. It has own implementations for pre/post Vista
     * but return a uniformly correct value.
     */
    virtual void seek(uint64_t record_id) = 0;

    /**
     * read the next eventlog record
     * Note: records are retrieved from the api in chunks, so this read will be
     * quick most of the time but occasionally cause a fetch via api that takes
     * longer
     */
    virtual EventLogRecordBase *readRecord() = 0;

    // return the ID of the last record in eventlog
    virtual uint64_t getLastRecordId() = 0;

    // checks that log really exists
    [[nodiscard]] virtual bool isLogValid() const = 0;
};

// Official CheckMK Event Log API
/// \brief - open event log using one of available mode
std::unique_ptr<EventLogBase> OpenEvl(const std::wstring &name, bool vista_api);

/// \brief - scan existing event log
std::pair<uint64_t, cfg::EventLevels> ScanEventLog(EventLogBase &log,
                                                   uint64_t pos,
                                                   cfg::EventLevels level);

using EvlProcessor = std::function<bool(const std::string &)>;

// third call
uint64_t PrintEventLog(EventLogBase &log, uint64_t from_pos,
                       cfg::EventLevels level, bool hide_context,
                       SkipDuplicatedRecords skip,
                       const EvlProcessor &processor);
// internal
inline uint64_t choosePos(uint64_t last_read_pos) {
    return cfg::kFromBegin == last_read_pos ? 0 : last_read_pos + 1;
}

}  // namespace cma::evl
#endif  // EventLogBase_h
