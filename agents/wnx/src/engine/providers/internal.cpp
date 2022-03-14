
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

namespace cma::provider {

// Confirmed values with AB from LA(3600s)
std::unordered_map<std::string_view, std::chrono::seconds> g_delays_on_fail = {
    {kDotNetClrMemory, cma::cfg::G_DefaultDelayOnFail},  //
    {kWmiWebservices, cma::cfg::G_DefaultDelayOnFail},   //
    {kWmiCpuLoad, cma::cfg::G_DefaultDelayOnFail},       //
    {kMsExch, cma::cfg::G_DefaultDelayOnFail},           //
    {kOhm, cma::cfg::G_DefaultDelayOnFail},

    // end of the real sections
    {kBadWmi, cma::cfg::G_DefaultDelayOnFail},  // used to testing
};

namespace {
/// Separates string by first space
// "word left over" => ["word", "left over"]
std::pair<std::string, std::string> SplitStringBySpace(
    const std::string &line) {
    auto end = line.find_first_of(' ');
    if (end == std::string::npos) {
        return {line, {}};
    }
    // split
    return {line.substr(0, end), line.substr(end + 1)};
}
}  // namespace

/// returns tuple with parsed command line
// {marker of Answer, First, Leftover}
std::tuple<uint64_t, std::string, std::string> ParseCommandLine(
    const std::string &line) noexcept {
    uint64_t marker = 0;
    try {
        auto [marker_str, leftover] = SplitStringBySpace(line);
        marker = std::stoull(marker_str, nullptr,
                             10);  // may generate exception

        // Second parameter is section name
        if (!leftover.empty()) {
            // get second parameter
            auto [section_name_str, leftover_last] =
                SplitStringBySpace(leftover);

            // make valid return
            return {marker, section_name_str, leftover_last};
        }
    } catch (const std::exception &e) {
        XLOG::l("Command line '{}' is not valid, exception: '{}'", line,
                e.what());
        marker = 0;
    }

    return {marker, std::string(section::kUseEmbeddedName), ""};
}

void Basic::registerOwner(cma::srv::ServiceProcessor *sp) { host_sp_ = sp; }

std::string Basic::generateContent(std::string_view section_name,
                                   bool force_generation) {
    auto real_name =
        section_name == section::kUseEmbeddedName ? uniq_name_ : section_name;

    if (!force_generation && !cfg::groups::global.allowedSection(real_name)) {
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

        if (headerless_) return section_body;
        // print header with default or commanded section name
        return makeHeader(section_name) + section_body;
    } catch (const std::exception &e) {
        XLOG::l.crit("Exception {} in {}", e.what(), uniq_name_);
    } catch (...) {
        XLOG::l.crit("Exception UNKNOWN in {}", uniq_name_);
    }
    return {};
}

bool Basic::isAllowedByCurrentConfig() const {
    auto name = getUniqName();
    bool allowed = cfg::groups::global.allowedSection(name);
    return allowed;
}

bool Basic::isAllowedByTime() const {
    return std::chrono::steady_clock::now() > allowed_from_time_;
}

void Basic::loadStandardConfig() {
    enabled_ = cfg::GetVal(uniq_name_, cfg::vars::kEnabled, true);
    timeout_ = cfg::GetVal(uniq_name_, cfg::vars::kTimeout, 0);
}

void Basic::registerCommandLine(const std::string &command_line) {
    auto [ip, leftover] = SplitStringBySpace(command_line);
    ip_ = ip;
}

void Basic::setupDelayOnFail() noexcept {
    // setup delay on fail
    try {
        const auto &delay_in_seconds = g_delays_on_fail[uniq_name_];
        delay_on_fail_ = delay_in_seconds;
    } catch (const std::exception &) {
        // do nothing here
    }
}

// if section fails then we may set time point in the future to avoid
// calling section too soon
void Basic::disableSectionTemporary() {
    if (delay_on_fail_.count() == 0) return;

    allowed_from_time_ = std::chrono::steady_clock::now();
    allowed_from_time_ += delay_on_fail_;

    {
        // System clock is not Steady Clock
        auto sys_clock = std::chrono::system_clock::now() + delay_on_fail_;
        XLOG::l.w(
            "Resetting time for earliest start of the section '{}' at '{}'",
            getUniqName(), cma::tools::TimeToString(sys_clock));
    }
}

// returns true when data exist.
bool Basic::sendGatheredData(const std::string &command_line) {
    // command line parser
    auto [marker, section_name, leftover] = ParseCommandLine(command_line);

    auto section = generateContent(section_name);

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

bool Synchronous::startExecution(
    const std::string &internal_port,  // format "type:value", where type:
                                       // mail - for mail slot
                                       // asio - for TCP
                                       // grpc - for GRPC
                                       // rest - for Rest
    const std::string &command_line    // format "id name whatever"
) {
    try {
        carrier_.establishCommunication(internal_port);
        sendGatheredData(command_line);

    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " - unexpected exception {}", e.what());
    }
    carrier_.shutdownCommunication();
    return true;
}

bool Asynchronous::startExecution(const std::string &internal_port,
                                  const std::string &command_line) {
    using namespace std::chrono_literals;
    if (thread_.joinable()) {
        XLOG::l.crit("Attempt to start service twice, no way!");
        return false;
    }

    threadProc(internal_port, command_line, 0ms);
    return true;
}

// #TODO gtest
bool Asynchronous::stop(bool wait) {
    std::unique_lock lk(lock_stopper_);
    stop_requested_ = true;
    stop_thread_.notify_one();
    lk.unlock();
    if (wait && thread_.joinable()) {
        thread_.join();
    }

    return true;
}

void Asynchronous::threadProc(
    const std::string &internal_port,  // address to send data
    const std::string &command_line,   // "Marker SectionName LeftOver"
    std::chrono::milliseconds period)  // for infinite running(FUTURE!)
{
    using namespace std::chrono_literals;

    try {
        carrier_.establishCommunication(internal_port);

        while (true) {
            auto tm = std::chrono::steady_clock::now();

            sendGatheredData(command_line);

            if (period == 0ms) {
                break;
            }

            std::unique_lock l(lock_stopper_);
            auto stop = stop_thread_.wait_until(
                l, tm + period, [this]() { return stop_requested_; });

            if (stop) {
                break;
            }
        }
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " - unexpected exception {}", e.what());
    }
    carrier_.shutdownCommunication();
}
}  // namespace cma::provider
