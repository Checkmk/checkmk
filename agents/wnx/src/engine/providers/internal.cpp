#include "stdafx.h"

#include "providers/internal.h"

#include <ctime>
#include <cerrno>

#include <chrono>
#include <functional>
#include <mutex>
#include <string>
#include <tuple>

#include "common/mailslot_transport.h"
#include "wnx/cfg.h"

using namespace std::chrono_literals;

namespace cma::provider {

namespace {
tm GetTimeAsTm(std::chrono::system_clock::time_point time_point) {
    const auto in_time_t = std::chrono::system_clock::to_time_t(time_point);
    tm buf{};
    errno = 0;
    if (localtime_s(&buf, &in_time_t) != 0) {
        XLOG::d.e("GetTimeAsTm: localtime_s failed with errno {}", errno);
    }
    return buf;
}

std::string TimeToString(std::chrono::system_clock::time_point time_point) {
    std::stringstream sss;
    const auto time_value = GetTimeAsTm(time_point);
    sss << std::put_time(&time_value, "%Y-%m-%d %T");
    return sss.str();
}

// Confirmed values with AB from LA(3600s)
const std::unordered_map<std::string_view, std::chrono::seconds> &
GetDelaysOnFail() {
    const static std::unordered_map<std::string_view, std::chrono::seconds>
        delays_on_fail = {
            {kDotNetClrMemory, 0s},                        //
            {kWmiWebservices, cfg::G_DefaultDelayOnFail},  //
            {kWmiCpuLoad, 0s},                             //
            {kMsExch, cfg::G_DefaultDelayOnFail},          //
            {kOhm, cfg::G_DefaultDelayOnFail},

            // end of the real sections
            {kBadWmi, cfg::G_DefaultDelayOnFail},  // used to testing
            {"OhmBad", 1500s},                     // used to testing
        };
    return delays_on_fail;
}

/// Separates string by first space
/// "word left over" => ["word", "left over"]
std::pair<std::string, std::string> SplitStringBySpace(
    const std::string &line) {
    auto table = tools::SplitString(line, " ", 1);
    switch (table.size()) {
        case 0U:
            // impossible
            return {std::string{}, std::string{}};
        case 2U:
            // standard
            return std::pair{table[0], table[1]};
        default:
            // last arg
            return std::pair{table[0], std::string{}};
    }
}
}  // namespace

/// returns tuple with parsed command line
/// {marker of Answer, First, Leftover}
std::tuple<uint64_t, std::string, std::string> ParseCommandLine(
    const std::string &line) noexcept {
    uint64_t marker = 0;
    try {
        const auto &[marker_str, leftover] = SplitStringBySpace(line);
        marker = std::stoull(marker_str, nullptr, 10);  // exception!

        // Next parameter is section name
        if (!leftover.empty()) {
            const auto &[section_name_str, leftover_last] =
                SplitStringBySpace(leftover);

            return {marker, section_name_str, leftover_last};
        }
    } catch (const std::exception &e) {
        XLOG::l("Command line '{}' is not valid, exception: '{}'", line, e);
        marker = 0;
    }

    return {marker, std::string(section::kUseEmbeddedName), ""};
}

void Basic::registerOwner(srv::ServiceProcessor *sp) noexcept { host_sp_ = sp; }

std::string Basic::generateContent(std::string_view section_name,
                                   bool force_generation) {
    auto real_name =
        section_name == section::kUseEmbeddedName ? uniq_name_ : section_name;

    if (!force_generation && !cfg::groups::g_global.allowedSection(real_name)) {
        XLOG::t("The section \"{}\" is disabled in config", real_name);
        return {};
    }

    try {
        auto section_body = makeBody();
        if (section_body.empty()) {
            XLOG::d("Section '{}' cannot provide data", uniq_name_);
            return {};
        }
        // header-less mode is for the Plugins and Local
        return headerless_ ? section_body
                           : makeHeader(section_name) + section_body;
    } catch (const std::exception &e) {
        XLOG::l.crit("Exception {} in {}", e.what(), uniq_name_);
    } catch (...) {
        XLOG::l.crit("Exception UNKNOWN in {}", uniq_name_);
    }
    return {};
}

bool Basic::isAllowedByCurrentConfig() const {
    return cfg::groups::g_global.allowedSection(getUniqName());
}

bool Basic::isAllowedByTime() const noexcept {
    return std::chrono::steady_clock::now() > allowed_from_time_;
}

void Basic::loadStandardConfig() noexcept {
    enabled_ = cfg::GetVal(uniq_name_, cfg::vars::kEnabled, true);
    timeout_ = cfg::GetVal(uniq_name_, cfg::vars::kTimeout, 0);
}

void Basic::registerCommandLine(const std::string &command_line) {
    const auto &[ip, _] = SplitStringBySpace(command_line);
    ip_ = ip;
}

void Basic::setupDelayOnFail() noexcept {
    try {
        const auto &delay_in_seconds = GetDelaysOnFail().at(uniq_name_);
        delay_on_fail_ = delay_in_seconds;
    } catch (const std::out_of_range &) {
        XLOG::l.crit("Unsupported section name {}", uniq_name_);
        delay_on_fail_ = std::chrono::seconds(0);
    }
}

// if section fails then we may set time point in the future to avoid
// calling section too soon
void Basic::disableSectionTemporary() {
    if (delay_on_fail_.count() == 0) {
        return;
    }

    allowed_from_time_ = std::chrono::steady_clock::now();
    allowed_from_time_ += delay_on_fail_;

    // report using _system_ clock
    const auto sys_clock = std::chrono::system_clock::now() + delay_on_fail_;
    XLOG::d.w("Resetting time for earliest start of the section '{}' at '{}'",
              getUniqName(), TimeToString(sys_clock));
}

/// true when data exist.
bool Basic::sendGatheredData(const std::string &command_line) {
    const auto &[marker, section_name, leftover] =
        ParseCommandLine(command_line);

    auto section = generateContent(section_name);

    if (!section.empty()) {
        if (section.back() == '\0' || section.back() == '\n') {
            section.pop_back();  // some plugins may add zero. remove it
        }
        carrier_.sendData(uniq_name_, marker, section.c_str(), section.size());
        return true;
    }

    // empty data are send to unblock waiters on server side
    carrier_.sendData(uniq_name_, marker, nullptr, 0);
    return false;
}

/// port format: "type:value", where type:
/// mail - for mail slot
/// asio - for TCP
/// grpc - for GRPC
/// rest - for Rest
/// id format: any string
bool Synchronous::startExecution(const std::string &internal_port,
                                 const std::string &command_line) {
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
    if (thread_.joinable()) {
        XLOG::l.crit("Attempt to start service twice, no way!");
        return false;
    }
    threadProc(internal_port, command_line, 0ms);
    return true;
}

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
    try {
        carrier_.establishCommunication(internal_port);

        while (true) {
            const auto tm = std::chrono::steady_clock::now();
            sendGatheredData(command_line);
            if (period == 0ms) {
                break;
            }
            std::unique_lock l(lock_stopper_);
            const auto stop = stop_thread_.wait_until(
                l, tm + period, [this] { return stop_requested_; });
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
