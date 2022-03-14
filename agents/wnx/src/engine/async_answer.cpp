
// provides basic api to start and stop service

#include "stdafx.h"

#include "async_answer.h"

#include <chrono>
#include <cstdint>
#include <mutex>
#include <ranges>
#include <string>
#include <vector>

#include "common/cfg_info.h"
#include "logger.h"
#include "section_header.h"       // names
#include "windows_service_api.h"  // global situation

using std::chrono::milliseconds;
using std::chrono::steady_clock;

namespace cma::srv {

bool AsyncAnswer::isAnswerOlder(milliseconds period) const {
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

bool AsyncAnswer::waitAnswer(milliseconds to_wait) {
    std::unique_lock lk(lock_);
    ON_OUT_OF_SCOPE(sw_.stop());
    return cv_ready_.wait_until(
        lk, steady_clock::now() + to_wait, [this]() -> bool {
            // check for global exit
            if (IsGlobalStopSignaled()) {
                XLOG::d.i("Breaking Answer on stop");
                return true;
            }
            return awaited_segments_ <= received_segments_;
        });
}

namespace {
// combines two vectors together
// on exception(malicious plugin @ 32 bit OS) returns false
bool AddVectorGracefully(std::vector<uint8_t> &out_data,
                         const std::vector<uint8_t> &in_data) {
    if (in_data.empty()) return true;

    auto old_size = out_data.size();
    try {
        // a bit of optimization
        out_data.reserve(out_data.size() + in_data.size());
        out_data.insert(out_data.end(), in_data.begin(), in_data.end());

        // divider after every section with data
        out_data.push_back(static_cast<uint8_t>('\n'));
        return true;
    } catch (const std::exception &e) {
        // return to invariant...
        XLOG::l(XLOG_FLINE + "- disaster '{}'", e.what());
        out_data.resize(old_size);
    }

    return false;
}
}  // namespace

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

bool AsyncAnswer::prepareAnswer(std::string_view ip) {
    std::lock_guard lk(lock_);

    if (!external_ip_.empty() || awaited_segments_ != 0 ||
        received_segments_ != 0) {
        XLOG::l("Answer is in use.");
        return false;
    }

    dropDataNoLock();
    tp_id_ = GenerateAnswerId();
    external_ip_ = ip;
    sw_.start();
    return true;
}

// sorted list of all received sections
std::vector<std::string> AsyncAnswer::segmentNameList() const {
    std::unique_lock lk(lock_);
    std::vector<std::string> list;
    for (const auto &s : segments_) {
        list.emplace_back(s.name_);
    }
    lk.unlock();
    std::ranges::sort(list);
    return list;
}

bool AsyncAnswer::addSegment(
    const std::string &section_name,  // name
    const AnswerId &answer_id,        // "password"
    const std::vector<uint8_t> &data  // data for section
) {
    std::lock_guard lk(lock_);
    if (answer_id != tp_id_) {
        XLOG::d("Invalid attempt to add data '{}'", section_name);
        return false;
    }

    for (const auto &s : segments_) {
        if (s.name_ == section_name) {
            XLOG::l("Section '{}' tries to store data twice. F-f",
                    section_name);
            return false;
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
    } catch (const std::exception &e) {
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
