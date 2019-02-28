
#include "stdafx.h"

#include "eventlogbase.h"
#include "eventlogstd.h"
#include "eventlogvista.h"

namespace cma::evl {
std::unique_ptr<cma::evl::EventLogBase> OpenEvl(const std::wstring &Name,
                                                bool VistaApi) {
    if (VistaApi && g_evt.close)
        return std::unique_ptr<EventLogBase>(new EventLogVista(Name));

    return std::unique_ptr<EventLogBase>(new EventLog(Name));
}

std::pair<uint64_t, cma::cfg::EventLevels> ScanEventLog(
    EventLogBase &log, uint64_t previouslyReadId, cma::cfg::EventLevels level) {
    // we must seek past the previously read event - if there was one
    const uint64_t seekPosition =
        previouslyReadId + (cma::cfg::kInitialPos == previouslyReadId ? 0 : 1);

    cma::cfg::EventLevels worstState = cma::cfg::EventLevels::kAll;
    uint64_t lastRecordId = previouslyReadId;

    // WARNING:
    // seek implementations for pre-Vista and post-Vista are completely
    // different.
    // seek *must not* return any value as it is different between pre/post
    // Vista.
    log.seek(seekPosition);
    while (1) {
        auto record = log.readRecord();
        if (record == nullptr) break;
        ON_OUT_OF_SCOPE(delete record);

        lastRecordId = record->recordId();
        auto calculated = record->calcEventLevel(level);
        worstState = std::max(worstState, calculated);
    }

    return {lastRecordId, worstState};
}

std::pair<uint64_t, std::string> PrintEventLog(EventLogBase &log,
                                               uint64_t previouslyReadId,
                                               cma::cfg::EventLevels level,
                                               bool HideContext) {
    // we must seek past the previously read event - if there was one
    const uint64_t seekPosition =
        previouslyReadId + (cma::cfg::kInitialPos == previouslyReadId ? 0 : 1);

    uint64_t lastRecordId = previouslyReadId;

    // WARNING:
    // seek implementations for pre-Vista and post-Vista are completely
    // different.
    // seek *must not* return any value as it is different between pre/post
    // Vista.
    log.seek(seekPosition);
    std::string out;
    while (1) {
        auto record = log.readRecord();

        if (record == nullptr) break;
        ON_OUT_OF_SCOPE(delete record);

        lastRecordId = record->recordId();
        auto str = record->stringize(level, HideContext);
        if (!str.empty()) out += str;
    }

    return {lastRecordId, out};
}  // namespace cma::evl

}  // namespace cma::evl
