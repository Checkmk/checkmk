
// provides basic api to start and stop service

#include "stdafx.h"

#include <chrono>
#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

#include "common/cfg_info.h"
#include "tools/_xlog.h"

#include "async_answer.h"

namespace cma::srv {

bool AsyncAnswer::isAnswerOlder(std::chrono::milliseconds Milli) const {
    using namespace std::chrono;
    auto tp = steady_clock::now();
    std::lock_guard lk(lock_);
    if (std::chrono::duration_cast<std::chrono::milliseconds>(tp - tp_id_) >
        Milli)
        return true;

    return false;
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

// kills data in any case
// return gathered data back
AsyncAnswer::DataBlock AsyncAnswer::getDataAndClear() {
    std::lock_guard lk(lock_);
    try {
        auto v = std::move(data_);
        dropDataNoLock();
        return v;
    } catch (const std::exception& e) {
        xlog::l(XLOG_FLINE + " - no-no-no %s", e.what());
        dropDataNoLock();
        return {};
    }
}

bool AsyncAnswer::prepareAnswer(std::string Ip) {
    std::lock_guard lk(lock_);
    if (external_ip_ != "" || awaiting_segments_ || received_segments_) {
        // #TODO check IP and add to list #ERROR here
        return false;
    }
    dropDataNoLock();
    external_ip_ = Ip;
    awaiting_segments_ = 0;
    received_segments_ = 0;
    return true;
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
        Out.push_back((uint8_t)'\n');
    } catch (const std::exception& e) {
        // return invariant...
        XLOG::l(XLOG_FLINE + "- catastrophe {}", e.what());
        Out.resize(old_size);
        return false;
    }
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
        xlog::d("Invalid attempt to add data");
        return false;
    }

    for (const auto& s : segments_) {
        if (s.name_ == SectionName) {
            xlog::l("Section %s tries to store data twice. F-f",
                    SectionName.c_str());
            return false;  // duplicated section run
        }
    }

    try {
        segments_.push_back({SectionName, Data.size()});
        // reserve + array math
        if (Data.size()) {
            if (!AddVectorGracefully(data_, Data)) segments_.back().length_ = 0;
        }
    } catch (const std::exception& e) {
        // not possible, but we have to check
        xlog::l(XLOG_FLINE + "-exception %s", e.what());
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
