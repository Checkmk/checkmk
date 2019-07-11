
// provides basic api to start and stop service

#include "stdafx.h"

#include "async_answer.h"

#include <chrono>
#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

#include "common/cfg_info.h"
#include "logger.h"
#include "tools/_xlog.h"

namespace cma::srv {

bool AsyncAnswer::isAnswerOlder(std::chrono::milliseconds Milli) const {
    using namespace std::chrono;
    auto tp = steady_clock::now();

    std::lock_guard lk(lock_);
    return duration_cast<milliseconds>(tp - tp_id_) > Milli;
}

void AsyncAnswer::dropAnswer() {
    std::lock_guard lk(lock_);
    dropDataNoLock();
}

// returns true when answer is ready, false when timeout expires but not ready
bool AsyncAnswer::waitAnswer(std::chrono::milliseconds WaitInterval) {
    using namespace std::chrono;

    std::unique_lock lk(lock_);
    return cv_ready_.wait_until(
        lk, steady_clock::now() + WaitInterval,
        [this]() -> bool { return awaiting_segments_ <= received_segments_; });
}

// combines two vectors together
// in case of exception returns false
// Caller MUST Fix section size!
static bool AddVectorGracefully(std::vector<uint8_t>& Out,
                                const std::vector<uint8_t>& In) noexcept {
    auto old_size = Out.size();
    // we have theoretical possibility of exception here
    try {
        // a bit of optimization
        Out.reserve(Out.size() + In.size());
        Out.insert(Out.end(), In.begin(), In.end());

        // divider after every section with data
        Out.push_back(static_cast<uint8_t>('\n'));
    } catch (const std::exception& e) {
        // return to invariant...
        XLOG::l(XLOG_FLINE + "- disaster '{}'", e.what());
        Out.resize(old_size);
        return false;
    }
    return true;
}

// kills data in any case
// return gathered data back
AsyncAnswer::DataBlock AsyncAnswer::getDataAndClear() {
    std::lock_guard lk(lock_);
    try {
        if (order_ == Order::plugins_last) {
            if (!plugins_.empty()) AddVectorGracefully(data_, plugins_);
            if (!local_.empty()) AddVectorGracefully(data_, local_);
            plugins_.clear();
            local_.clear();
        }

        auto v = std::move(data_);
        dropDataNoLock();
        return v;
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FLINE + " - no-no-no '{}'", e.what());
        dropDataNoLock();
        return {};
    }
}

bool AsyncAnswer::prepareAnswer(std::string_view Ip) noexcept {
    std::lock_guard lk(lock_);

    if (!external_ip_.empty() || awaiting_segments_ != 0 ||
        received_segments_ != 0)
        return false;

    dropDataNoLock();
    external_ip_ = Ip;
    awaiting_segments_ = 0;
    received_segments_ = 0;
    plugins_.clear();
    local_.clear();
    return true;
}

// Reporting Function, which called by the section plugins and providers
// Thread safe!
bool AsyncAnswer::addSegment(
    const std::string SectionName,   // name
    const AnswerId Id,               // "password"
    const std::vector<uint8_t> Data  // data for section
) {
    std::lock_guard lk(lock_);
    if (Id != tp_id_) {
        XLOG::d("Invalid attempt to add data '{}'", SectionName);
        return false;
    }

    for (const auto& s : segments_) {
        if (s.name_ == SectionName) {
            XLOG::l("Section '{}' tries to store data twice. F-f", SectionName);
            return false;  // duplicated section run
        }
    }

    try {
        segments_.push_back({SectionName, Data.size()});

        // reserve + array math
        if (order_ == Order::plugins_last && SectionName == "plugins") {
            plugins_ = Data;
        } else if (order_ == Order::plugins_last && SectionName == "local") {
            local_ = Data;
        } else if (!Data.empty()) {
            if (!AddVectorGracefully(data_, Data)) segments_.back().length_ = 0;
        }
    } catch (const std::exception& e) {
        // not possible, but we have to check
        XLOG::l(XLOG_FLINE + "-exception '{}'", e.what());
    }

    received_segments_++;

    if (awaiting_segments_ <= received_segments_) {
        // theoretically on answer may wait many threads
        // so notify all.
        cv_ready_.notify_all();
    }

    return true;
}

// resets data, internal use only
void AsyncAnswer::dropDataNoLock() {
    tp_id_ = GenerateAnswerId();
    awaiting_segments_ = 0;
    received_segments_ = 0;
    data_.resize(0);
    segments_.resize(0);
    external_ip_ = "";
}
}  // namespace cma::srv
