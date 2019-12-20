#ifndef EventLogBase_h
#define EventLogBase_h

#include <fmt/format.h>
#include <time.h>

#include <functional>
#include <memory>
#include <string>

#include "common/cfg_info.h"
#include "common/wtools.h"

namespace cma::evl {
class EventLogRecordBase {
public:
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

    virtual uint64_t recordId() const = 0;
    virtual uint16_t eventId() const = 0;
    virtual uint16_t eventQualifiers() const = 0;
    virtual time_t timeGenerated() const = 0;
    virtual std::wstring source() const = 0;
    virtual Level eventLevel() const = 0;
    virtual std::wstring makeMessage() const = 0;

    std::string stringize(cma::cfg::EventLevels Required,
                          bool HideTrash) const {
        // convert UNIX timestamp to local time
        auto ch = getEventSymbol(Required);
        if (HideTrash && ch == '.') return {};

        time_t time_generated = static_cast<time_t>(timeGenerated());
        struct tm *t = localtime(&time_generated);
        char timestamp[64];
        strftime(timestamp, sizeof(timestamp), "%b %d %H:%M:%S", t);

        // source is the application that produced the event
        std::string source_name = wtools::ConvertToUTF8(source());
        std::replace(source_name.begin(), source_name.end(), ' ', '_');

        return fmt::format("{} {} {}.{} {} {}\n",
                           ch,                 // char symbol
                           timestamp,          //
                           eventQualifiers(),  //
                           eventId(),          //
                           source_name,        //
                           wtools::ConvertToUTF8(makeMessage()));
    }

    // for output in port
    char getEventSymbol(cma::cfg::EventLevels Required) const {
        switch (eventLevel()) {
            case Level::error:
                return 'C';
            case Level::warning:
                return 'W';
            case Level::information:
            case Level::audit_success:
            case Level::success:
                if (Required == cma::cfg::EventLevels::kAll)
                    return 'O';
                else
                    return '.';  // potential drop of context
            case Level::audit_failure:
                return 'C';
            default:
                return 'u';
        }
    }

    // decode windows level to universal
    cma::cfg::EventLevels calcEventLevel(cma::cfg::EventLevels Required) const {
        switch (eventLevel()) {
            case Level::error:
                return cma::cfg::EventLevels::kCrit;
            case Level::warning:
                return cma::cfg::EventLevels::kWarn;
            case Level::information:
            case Level::audit_success:
            case Level::success:
                return cma::cfg::EventLevels::kAll;
            case Level::audit_failure:
                return cma::cfg::EventLevels::kCrit;
            default:
                return cma::cfg::EventLevels::kWarn;
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
    virtual std::wstring getName() const = 0;

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
    virtual bool isLogValid() const = 0;
};

// Official API
// first call
std::unique_ptr<cma::evl::EventLogBase> OpenEvl(const std::wstring &Name,
                                                bool VistaApi);

// second call
std::pair<uint64_t, cma::cfg::EventLevels> ScanEventLog(
    EventLogBase &log, uint64_t previouslyReadId, cma::cfg::EventLevels level);

using EvlProcessor = std::function<bool(const std::string &)>;

// third call
uint64_t PrintEventLog(EventLogBase &log, uint64_t from_pos,
                       cma::cfg::EventLevels level, bool hide_context,
                       EvlProcessor processor);
// internal
inline uint64_t choosePos(uint64_t last_read_pos) {
    return cma::cfg::kFromBegin == last_read_pos ? 0 : last_read_pos + 1;
}

}  // namespace cma::evl
#endif  // EventLogBase_h
