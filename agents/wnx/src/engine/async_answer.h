
// provides basic api to start and stop service

#pragma once
#ifndef answer_h__
#define answer_h__

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

namespace cma::srv {
using AnswerId = std::chrono::time_point<std::chrono::steady_clock>;
static AnswerId GenerateAnswerId() { return std::chrono::steady_clock::now(); }

// MAIN CLASS to gather all data for CMA on kick from Monitor
// not POD
// Thread-safe!
// During creation gets unique id to be used for communication with
// plugins and providers
// Answer consists from 0 or more segments
// Segment consists from 0 or more sections
// Segments is provide from execution unit(exe or internal thread)
class AsyncAnswer {
public:
    using DataBlock = std::vector<uint8_t>;
    enum class Order { random, plugins_last };
    AsyncAnswer()
        : timeout_(5), awaiting_segments_(0), tp_id_(GenerateAnswerId()) {}

    bool isAnswerOlder(std::chrono::milliseconds Milli) const;

    auto getId() const { return tp_id_; }

    //
    bool isAnswerInUse() const {
        std::lock_guard lk(lock_);
        return isAnswerInUseNoLock();
    }

    void dropAnswer();  // owner does it, reset all to initial state

    //
    bool waitAnswer(std::chrono::milliseconds MillisecondsToWait);

    void exeKickedCount(int Count) {
        std::lock_guard lk(lock_);
        awaiting_segments_ = Count;
    }

    // thread safe
    // kills all data gathered(dropAnswer)
    // returns all gathered data back
    DataBlock getDataAndClear();

    // #TODO gtest
    auto getAllClear() {}

    bool prepareAnswer(std::string_view Ip) noexcept;

    // Reporting Function, which called by the sections
    // #TODO gtest
    bool addSegment(const std::string SegmentProviderName,  // name
                    const AnswerId RequiredAnswerId,        // "password"
                    const std::vector<uint8_t> data         // data for section
    );

    // #TODO gtest
    auto awaitingSegments() const {
        std::lock_guard lk(lock_);
        return awaiting_segments_;
    }

    // #TODO gtest
    auto receivedSegments() const {
        std::lock_guard lk(lock_);
        return received_segments_;
    }

    // #TODO gtest
    void newTimeout(int Timeout) {
        std::lock_guard lk(lock_);
        if (Timeout > timeout_) timeout_ = Timeout;
    }

    // #TODO gtest
    int timeout() const {
        std::lock_guard lk(lock_);
        return timeout_;
    }

private:
    bool isAnswerInUseNoLock() const {
        return !external_ip_.empty() || !segments_.empty() ||
               awaiting_segments_ != 0 || received_segments_ != 0;
    }

    struct SegmentInfo {
        std::string name_;
        size_t length_;
    };

    void dropDataNoLock();

    mutable std::mutex lock_;

    std::string external_ip_;  // who initiated request
    AnswerId tp_id_;           // time when request hit processing,
                               // also used as a password
                               // for plugins and providers too late or too lazy
    DataBlock data_;           // our pretty data

    uint32_t awaiting_segments_;  // how many sections are awaited
    uint32_t received_segments_;  // how many sections are received

    int timeout_;  // seconds

    std::vector<SegmentInfo> segments_;

    // awaiting_sections_ used for predicate
    std::condition_variable cv_ready_;

    DataBlock plugins_;
    DataBlock local_;

    const Order order_ = Order::plugins_last;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class AsyncAnswerTest;
    FRIEND_TEST(AsyncAnswerTest, Base);
#endif
};
}  // namespace cma::srv

#endif  // answer_h__
