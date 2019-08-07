
// provides basic api to start and stop service

#pragma once
#ifndef p_internal_h__
#define p_internal_h__

#include <chrono>
#include <condition_variable>
#include <mutex>
#include <string>
#include <string_view>

#include "carrier.h"
#include "common/stop_watch.h"
#include "section_header.h"

namespace cma::srv {
class ServiceProcessor;
}

namespace cma {

namespace provider {

// simple creator valid state name
// gtest [+]
inline std::string MakeStateFileName(const std::string& Name,
                                     const std::string& Ext,
                                     const std::string& Ip = "") {
    if (Name.empty() || Ext.empty()) {
        XLOG::l("Invalid parameters to MakeStateFileName '{}' '{}'", Name, Ext);
        return {};
    }

    std::string ip = Ip.empty() ? "" : " " + Ip;
    std::transform(ip.cbegin(), ip.cend(), ip.begin(),
                   [](char c) { return std::isalnum(c) ? c : L'_'; });

    auto out = Name + ip + Ext;

    return out;
}

class Basic {
public:
    Basic(const std::string_view& Name, char Separator = 0)
        : uniq_name_(Name)
        , separator_(Separator)
        , delay_on_fail_(0)
        , timeout_(0)
        , enabled_(true)
        , headerless_(false) {
        allowed_from_time_ = std::chrono::steady_clock::now();
    }
    virtual ~Basic() {}

    virtual bool startSynchronous(
        const std::string& InternalPort,  // format "type:value", where type:
        // mail - for mail slot
        // asio - for TCP
        // grpc - for GRPC
        // rest - for Rest
        const std::string& CommandLine,  // anything here
        std::chrono::milliseconds Period = std::chrono::milliseconds{0}) = 0;

    virtual bool stop(bool Wait = true) = 0;

    std::string getUniqName() const { return uniq_name_; }
    const std::string ip() const { return ip_; }

    // implemented only for very special providers which has to change
    // itself during generation of output(like plugins)
    virtual void updateSectionStatus() {}
    std::string generateContent(const std::string_view& SectionName,
                                bool ForceGeneration = false);

    virtual bool isAllowedByCurrentConfig() const;
    bool isAllowedByTime() const;

    // called in kick. NO AUTOMATION HERE.
    void loadStandardConfig();
    virtual void loadConfig() {}
    int timeout() const { return timeout_; }
    virtual void registerCommandLine(const std::string& CmdLine);

    virtual void preStart() noexcept {}
    uint64_t errorCount() const { return error_count_; }
    uint64_t resetError() { return error_count_.exchange(0); }

    char separator() const { return separator_; }

    void stopWatchStart() { sw_.start(); }
    uint64_t stopWatchStop() { return sw_.stop(); }

protected:
    wtools::StopWatch sw_;
    // conditionally(depending from the name of section) sets delay after error
    void setupDelayOnFail() noexcept;

    void setHeaderless() { headerless_ = true; }

    // to stop section from rerunning during time defined in setupDelayOnFail
    // usually related to the openhardware monitor
    void disableSectionTemporary();

    bool sendGatheredData(const std::string& CommandLine);
    virtual std::string makeHeader(const std::string_view SectionName) const {
        return section::MakeHeader(SectionName == cma::section::kUseEmbeddedName
                                       ? std::string_view(uniq_name_)
                                       : SectionName,
                                   separator_);
    }
    virtual std::string makeBody() = 0;

    const std::string uniq_name_;  // unique identification of section provider

    cma::carrier::CoreCarrier carrier_;  // transport
    std::chrono::time_point<std::chrono::steady_clock> allowed_from_time_;
    std::chrono::seconds
        delay_on_fail_;  // this value may be set when we have problems with
                         // obtaining data. Next try will be set from
                         // now + delay_on_fail_ if delay_on_fail_ is not 0
                         // check ToggleIf in legacy Agent

    int timeout_;  // may be set in...
    bool enabled_;
    // optional API to store info about errors used, for example by OHM
    uint64_t registerError() { return error_count_.fetch_add(1); }

private:
    bool headerless_;  // if true no makeHeader called during content generation
    std::string ip_;
    char separator_;
    std::atomic<uint64_t> error_count_ = 0;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class WmiProviderTest;
    FRIEND_TEST(WmiProviderTest, WmiAll);
    FRIEND_TEST(WmiProviderTest, BasicWmi);
    FRIEND_TEST(WmiProviderTest, BasicWmiDefaultsAndError);
#endif
};

// Reference *SYNC* Class for internal Sections
// use as a parent
class Synchronous : public Basic {
public:
    Synchronous(const std::string_view& Name, char Separator = 0)
        : Basic(Name, Separator) {}
    virtual ~Synchronous() {}

    bool startSynchronous(
        const std::string& InternalPort,  // format "type:value", where type:
        // mail - for mail slot
        // asio - for TCP
        // grpc - for GRPC
        // rest - for Rest
        const std::string& CommandLine,  // format "id name whatever"
        std::chrono::milliseconds Period = std::chrono::milliseconds{0});
    virtual bool stop(bool Wait = true) { return true; }  // rather not possible
};

// Reference *ASYNC* Class for internal Sections
// This class may work in Sync mode TOO.
// When you need choice, then  use this class
class Asynchronous : public Basic {
public:
    Asynchronous(const std::string_view& Name, char Separator = 0)
        : Basic(Name, Separator) {}
    virtual ~Asynchronous() {}

    // #TODO remove: this function is obsolete - no need be to more async
    virtual bool startAsynchronous(
        const std::string& InternalPort,  // format "type:value", where type:
        // mail - for mail slot
        // asio - for TCP
        // grpc - for GRPC
        // rest - for Rest
        const std::string& CommandLine,  // anything here
        bool Detached,                   // no waiting
        std::chrono::milliseconds Period = std::chrono::milliseconds{0});

    // use this function when switch between sync async is possible
    virtual bool startSynchronous(
        const std::string& InternalPort,  // format "type:value", where type:
        // mail - for mail slot
        // asio - for TCP
        // grpc - for GRPC
        // rest - for Rest
        const std::string& CommandLine,
        std::chrono::milliseconds Period = std::chrono::milliseconds{0});

    bool stop(bool Wait = true);

protected:
    // ASYNCHRONOUS PART:
    void threadProc(const std::string& InternalPort,
                    const std::string& CommandLine,
                    std::chrono::milliseconds Period) noexcept;

    // thread
    std::thread thread_;

    // stopping code(standard)
    std::condition_variable stop_thread_;
    mutable std::mutex lock_stopper_;
    bool stop_requested_ = false;
};

}  // namespace provider

};  // namespace cma

#endif  // p_internal_h__
