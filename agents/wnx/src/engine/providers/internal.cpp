
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/internal.h"

#include <chrono>
#include <functional>
#include <iostream>
#include <string>
#include <tuple>

#include "cfg.h"
#include "common/mailslot_transport.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma {

namespace provider {

// Confirmed values with AB from LA(3600s)
std::unordered_map<std::string_view, std::chrono::duration<int>>
    g_delays_on_fail = {
        {kDotNetClrMemory, cma::cfg::G_DefaultDelayOnFail},  //
        {kWmiWebservices, cma::cfg::G_DefaultDelayOnFail},   //
        {kWmiCpuLoad, cma::cfg::G_DefaultDelayOnFail},       //
        {kMsExch, cma::cfg::G_DefaultDelayOnFail},           //
        {kOhm, cma::cfg::G_DefaultDelayOnFail},

        // end of the real sections
        {kBadWmi, cma::cfg::G_DefaultDelayOnFail},  // used to testing
};

// pickup first word before space
// "word left over" => ["word", "ledt over"]
auto SplitStringLine(const std::string& Line) {
    using namespace cma::carrier;
    std::string cur_string = Line;
    std::string marker;
    {
        auto end = cur_string.find_first_of(' ');
        if (end == std::string::npos) {
            return std::make_tuple(Line, std::string());
        }
        // split
        auto segment = cur_string.substr(0, end);
        cur_string = cur_string.substr(end + 1);
        return std::make_tuple(segment, cur_string);
    }
    return std::make_tuple(std::string(), std::string());
}

// returns tuple with parsed command line
// {marker of Answer, First, Leftover}
std::tuple<uint64_t, std::string, std::string> ParseCommandLine(
    const std::string& Line) noexcept {
    using namespace cma::section;
    using namespace std;

    uint64_t marker = 0;
    try {
        auto [marker_str, leftover] = SplitStringLine(Line);
        marker = std::stoull(marker_str, nullptr,
                             10);  // may generate exception

        // Second parameter is section name
        if (!leftover.empty()) {
            // get second parameter
            auto [section_name_str, leftover_last] = SplitStringLine(leftover);

            // make valid return
            return {marker, section_name_str, leftover_last};
        }
    } catch (const std::exception& e) {
        XLOG::l("Command line '{}' is not valid, exception: '{}'", Line,
                e.what());
        marker = 0;
    }

    return {marker, std::string(kUseEmbeddedName), ""};
}

std::string Basic::generateContent(const std::string_view& SectionName,
                                   bool ForceGeneration) {
    auto real_name = SectionName == cma::section::kUseEmbeddedName
                         ? uniq_name_
                         : SectionName;
    if (!ForceGeneration &&
        !cma::cfg::groups::global.allowedSection(real_name)) {
        XLOG::t("The section \"{}\" is disabled in config", real_name);
        return {};
    }
    // print body
    try {
        auto section_body = makeBody();
        if (section_body.empty()) {
            XLOG::d("Section '{}' cannot provide data", uniq_name_);
            return {};
        }
        // header-less mode is for the Plugins and Local

        if (headerless_) return std::move(section_body);
        // print header with default or commanded section name
        return std::move(makeHeader(SectionName) + section_body);
    } catch (const std::exception& e) {
        XLOG::l.crit("Exception {} in {}", e.what(), uniq_name_);
    } catch (...) {
        XLOG::l.crit("Exception UNKNOWN in {}", uniq_name_);
    }
    return {};
}

bool Basic::isAllowedByCurrentConfig() const {
    auto name = getUniqName();
    bool allowed = cma::cfg::groups::global.allowedSection(name);
    return allowed;
}

bool Basic::isAllowedByTime() const {
    using namespace std::chrono;
    auto cur_time = steady_clock::now();
    return cur_time > allowed_from_time_;
}

void Basic::loadStandardConfig() {
    enabled_ = cma::cfg::GetVal(uniq_name_, cma::cfg::vars::kEnabled, true);
    timeout_ = cma::cfg::GetVal(uniq_name_, cma::cfg::vars::kTimeout, 0);
}

void Basic::registerCommandLine(const std::string& CmdLine) {
    auto [ip, leftover] = SplitStringLine(CmdLine);
    ip_ = ip;
}

void Basic::setupDelayOnFail() noexcept {
    // setup delay on fail
    try {
        const auto& delay_in_seconds = g_delays_on_fail[uniq_name_];
        delay_on_fail_ = delay_in_seconds;
    } catch (const std::exception&) {
        // do nothing here
    }
}

// if section fails then we may set time point in the future to avoid
// calling section too soon
void Basic::disableSectionTemporary() {
    using namespace std::chrono;
    if (delay_on_fail_.count() == 0) return;

    allowed_from_time_ = steady_clock::now();
    allowed_from_time_ += delay_on_fail_;

    {
        // System clock is not Steady Clock
        auto sys_clock = system_clock::now() + delay_on_fail_;
        XLOG::l.w(
            "Resetting time for earliest start of the section '{}' at '{}'",
            getUniqName(), cma::tools::TimeToString(sys_clock));
    }
}

// returns true when data exist.
bool Basic::sendGatheredData(const std::string& CommandLine) {
    using namespace std::chrono;

    // command line parser
    auto [marker, section_name, leftover] = ParseCommandLine(CommandLine);

    auto section = generateContent(section_name);
    // optional send something to log
    if (false) {
        auto title = fmt::format("from {} section", uniq_name_);
        carrier_.sendLog(uniq_name_, title.data(), title.length() + 1);
    }

    // send data
    if (!section.empty()) {
        if (section.back() == '\0')
            section.pop_back();  // some plugins may add zero. remove it
        if (section.back() == '\n') section.pop_back();
        carrier_.sendData(uniq_name_, marker, section.c_str(), section.size());
        return true;
    }

    // empty data are send to unblock waiters on server side
    carrier_.sendData(uniq_name_, marker, nullptr, 0);
    return false;
}

bool Synchronous::startSynchronous(
    const std::string& InternalPort,  // format "type:value", where type:
                                      // mail - for mail slot
                                      // asio - for TCP
                                      // grpc - for GRPC
                                      // rest - for Rest
    const std::string& CommandLine,   // format "id name whatever"
    std::chrono::milliseconds Period) {
    using namespace cma::section;
    try {
        carrier_.establishCommunication(InternalPort);
        sendGatheredData(CommandLine);

    } catch (const std::exception& e) {
        XLOG::l(XLOG_FUNC + " - unexpected exception {}", e.what());
    }
    carrier_.shutdownCommunication();
    return true;
}

bool Asynchronous::startAsynchronous(
    const std::string& InternalPort,
    const std::string& CommandLine,  // future use
    bool Detached,                   // no waiting, and no joining
    std::chrono::milliseconds Period) {
    if (thread_.joinable()) {
        XLOG::l("Attempt to start service twice, no way!");
        return false;
    }

    thread_ = std::thread(&Asynchronous::threadProc, this, InternalPort,
                          CommandLine,  // may be used in exe
                          Period);
    if (Detached) thread_.detach();
    return true;
}

// #TODO gtest
bool Asynchronous::startSynchronous(const std::string& InternalPort,
                                    const std::string& CommandLine,
                                    std::chrono::milliseconds Period) {
    using namespace std::chrono;
    // #TODO avoid possible race condition
    if (thread_.joinable()) {
        XLOG::l.crit("Attempt to start service twice, no way!");
        return false;
    }

    threadProc(InternalPort, CommandLine, 0ms);
    return true;
}

// #TODO gtest
bool Asynchronous::stop(bool Wait) {
    std::unique_lock lk(lock_stopper_);
    stop_requested_ = true;
    stop_thread_.notify_one();
    lk.unlock();
    if (Wait && thread_.joinable()) {
        thread_.join();
    }

    return true;
}

void Asynchronous::threadProc(
    const std::string& InternalPort,   // address to send data
    const std::string& CommandLine,    // "Marker SectionName LeftOver"
    std::chrono::milliseconds Period)  // for infinite running(FUTURE!)
    noexcept {
    using namespace std::chrono;
    using namespace cma::section;
    try {
        carrier_.establishCommunication(InternalPort);

        // command line parser
        auto [marker, section_name, leftover] = ParseCommandLine(CommandLine);

        for (;;) {
            auto tm = steady_clock().now();

            sendGatheredData(CommandLine);

            // automatically stopped when delay is 0
            if (Period == 0ms) break;

            // stopper by external signal
            std::unique_lock l(lock_stopper_);
            auto byebye = stop_thread_.wait_until(
                l, tm + Period, [this]() { return stop_requested_; });
            if (byebye) break;
        }
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FUNC + " - unexpected exception {}", e.what());
    }
    carrier_.shutdownCommunication();
}

}  // namespace provider
};  // namespace cma
