
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
#include "section_header.h"       // names
#include "windows_service_api.h"  // global situation

namespace cma::srv {

bool AsyncAnswer::isAnswerOlder(std::chrono::milliseconds period) const {
    using namespace std::chrono;
    auto tp = steady_clock::now();

    std::lock_guard lk(lock_);
    return duration_cast<milliseconds>(tp - tp_id_) > period;
}

void AsyncAnswer::dropAnswer() {
    std::lock_guard lk(lock_);
    dropDataNoLock();
    sw_.stop();
    sw_.reset();
}

// returns true when answer is ready, false when timeout expires but not ready
bool AsyncAnswer::waitAnswer(std::chrono::milliseconds to_wait) {
    using namespace std::chrono;

    std::unique_lock lk(lock_);
    ON_OUT_OF_SCOPE(sw_.stop());
    return cv_ready_.wait_until(
        lk, steady_clock::now() + to_wait, [this]() -> bool {
            // check for global exit
            if (cma::srv::IsGlobalStopSignaled()) {
                XLOG::l.i("Breaking Answer on stop");
                return true;
            }
            return awaited_segments_ <= received_segments_;
        });
}

// combines two vectors together
// in case of exception returns false
// Caller MUST Fix section size!
static bool AddVectorGracefully(std::vector<uint8_t>& Out,
                                const std::vector<uint8_t>& In) {
    if (In.empty()) return true;

    auto old_size = Out.size();
    // we have theoretical possibility of exception here

    try {
        // a bit of optimization
        Out.reserve(Out.size() + In.size());
        Out.insert(Out.end(), In.begin(), In.end());

        // divider after every section with data
        Out.push_back(static_cast<uint8_t>('\n'));
        return true;
    } catch (const std::exception& e) {
        // return to invariant...
        XLOG::l(XLOG_FLINE + "- disaster '{}'", e.what());
        Out.resize(old_size);
    }

    return false;
}

// kills data in any case
// return gathered data back
AsyncAnswer::DataBlock AsyncAnswer::getDataAndClear() {
    DataBlock v;

    std::lock_guard lk(lock_);
    if (order_ == Order::plugins_last) {
        AddVectorGracefully(data_, plugins_);
        AddVectorGracefully(data_, local_);
    }

    v = std::move(data_);
    dropDataNoLock();

    return v;
}

bool AsyncAnswer::prepareAnswer(std::string_view Ip) {
    std::lock_guard lk(lock_);

    if (!external_ip_.empty() || awaited_segments_ != 0 ||
        received_segments_ != 0) {
        XLOG::l("Answer is in use.");
        return false;
    }

    dropDataNoLock();
    tp_id_ = GenerateAnswerId();
    external_ip_ = Ip;
    sw_.start();
    return true;
}

// sorted list of all received sections
std::vector<std::string> AsyncAnswer::segmentNameList() {
    std::unique_lock lk(lock_);
    std::vector<std::string> list;
    for (const auto& s : segments_) list.emplace_back(s.name_);
    lk.unlock();
    std::sort(list.begin(), list.end());
    return list;
}

// Reporting Function, which called by the section plugins and providers
// Thread safe!
bool AsyncAnswer::addSegment(
    const std::string& section_name,  // name
    const AnswerId answer_id,         // "password"
    const std::vector<uint8_t>& data  // data for section
) {
    std::lock_guard lk(lock_);
    if (answer_id != tp_id_) {
        XLOG::d("Invalid attempt to add data '{}'", section_name);
        return false;
    }

    for (const auto& s : segments_) {
        if (s.name_ == section_name) {
            XLOG::l("Section '{}' tries to store data twice. F-f",
                    section_name);
            return false;  // duplicated section run
        }
    }

    try {
        segments_.push_back({section_name, data.size()});

        // reserve + array math
        if (order_ == Order::plugins_last &&
            section_name == cma::section::kPlugins) {
            plugins_ = data;
        } else if (order_ == Order::plugins_last &&
                   section_name == cma::section::kLocal) {
            local_ = data;
        } else if (!data.empty()) {
            if (!AddVectorGracefully(data_, data)) segments_.back().length_ = 0;
        }
    } catch (const std::exception& e) {
        // not possible, but we have to check
        XLOG::l(XLOG_FLINE + "-exception '{}'", e.what());
    }

    received_segments_++;

    if (awaited_segments_ <= received_segments_) {
        // theoretically on answer may wait many threads
        // so notify all.
        cv_ready_.notify_all();
    }

    return true;
}

// used to kick answer and check status
bool AsyncAnswer::tryBreakWait() {
    std::lock_guard lk(lock_);
    cv_ready_.notify_all();

    return true;
}

// resets data, internal use only
void AsyncAnswer::dropDataNoLock() {
    awaited_segments_ = 0;
    received_segments_ = 0;
    data_.clear();
    segments_.clear();
    external_ip_.clear();
    plugins_.clear();
    local_.clear();
}
}  // namespace cma::srv
