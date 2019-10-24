
#include "stdafx.h"

#include "eventlogbase.h"

#include "eventlogstd.h"
#include "eventlogvista.h"
#include "logger.h"

namespace cma::evl {
std::unique_ptr<cma::evl::EventLogBase> OpenEvl(const std::wstring &name,
                                                bool vista_api) {
    if (vista_api && g_evt.close)
        return std::unique_ptr<EventLogBase>(new EventLogVista(name));

    return std::unique_ptr<EventLogBase>(new EventLog(name));
}

std::pair<uint64_t, cma::cfg::EventLevels> ScanEventLog(
    EventLogBase &log, uint64_t pos, cma::cfg::EventLevels level) {
    // we must seek past the previously read event - if there was one
    const auto seek_pos = choosePos(pos);

    auto worst_state = cma::cfg::EventLevels::kAll;
    auto last_pos = pos;

    log.seek(seek_pos);
    while (1) {
        auto record = log.readRecord();
        if (record == nullptr) break;
        ON_OUT_OF_SCOPE(delete record);

        last_pos = record->recordId();
        auto calculated = record->calcEventLevel(level);
        worst_state = std::max(worst_state, calculated);
    }

    return {last_pos, worst_state};
}

// return any(!) positive number or 0.
// usually this is positive, because Windows keeps numbers very long
// and do not drop first entry id to 0 even after reset
uint64_t PrintEventLog(EventLogBase &log, uint64_t from_pos,
                       cma::cfg::EventLevels level, bool hide_context,
                       EvlProcessor processor) {
    // we must seek past the previously read event - if there was one
    const auto seek_pos = choosePos(from_pos);

    auto last_pos = from_pos;

    log.seek(seek_pos);

    while (1) {
        auto record = log.readRecord();

        if (record == nullptr) break;
        ON_OUT_OF_SCOPE(delete record);

        last_pos = record->recordId();
        auto str = record->stringize(level, hide_context);
        if (!str.empty())
            if (!processor(str)) break;
    }

    return last_pos;
}

}  // namespace cma::evl
