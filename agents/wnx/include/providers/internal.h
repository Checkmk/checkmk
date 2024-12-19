// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef P_INTERNAL_H
#define P_INTERNAL_H

#include <chrono>
#include <condition_variable>
#include <mutex>
#include <string>
#include <string_view>

#include "common/stop_watch.h"
#include "wnx/carrier.h"
#include "wnx/section_header.h"

namespace cma::srv {
class ServiceProcessor;
}  // namespace cma::srv

namespace cma::provider {

// simple creator valid state name
inline std::string MakeStateFileName(std::string_view name,
                                     std::string_view extension,
                                     std::string_view ip_address) {
    if (name.empty() || extension.empty()) {
        XLOG::l("Invalid parameters to MakeStateFileName '{}' '{}'", name,
                extension);
        return {};
    }

    std::string ip = ip_address.empty() ? "" : " " + std::string{ip_address};
    std::ranges::transform(
        ip, ip.begin(), [](char c) { return std::isalnum(c) != 0 ? c : L'_'; });

    return std::string{name} + ip + std::string{extension};
}

inline std::string MakeStateFileName(std::string_view name,
                                     std::string_view extension) {
    return MakeStateFileName(name, extension, "");
}

class Basic {
public:
    Basic(std::string_view name, char separator) noexcept
        : uniq_name_{name}, separator_{separator} {
        allowed_from_time_ = std::chrono::steady_clock::now();
    }
    explicit Basic(std::string_view name) noexcept : Basic(name, '\0') {}

    Basic(const Basic &) = delete;
    Basic &operator=(const Basic &) = delete;

    Basic(Basic &&) = delete;
    Basic &operator=(Basic &&) = delete;
    virtual ~Basic() = default;

    /// internal_port format "type:value", where type:
    /// mail - for mail slot
    /// asio - for TCP
    virtual bool startExecution(const std::string &internal_port,
                                const std::string &command_line) = 0;

    virtual bool stop(bool wait) = 0;

    std::string getUniqName() const noexcept { return uniq_name_; }
    std::string ip() const noexcept { return ip_; }

    /// maybe re-implemented for some special providers which
    /// has persistent data like cache. Example - Plugin providers
    virtual void updateSectionStatus() {}
    std::string generateContent(std::string_view section_name,
                                bool force_generation);
    std::string generateContent() {
        return generateContent(section::kUseEmbeddedName, false);
    }

    std::string generateContent(std::string_view section_name) {
        return generateContent(section_name, false);
    }

    virtual bool isAllowedByCurrentConfig() const;
    bool isAllowedByTime() const noexcept;
    auto allowedFromTime() const noexcept { return allowed_from_time_; }

    // called in kick. NO AUTOMATION HERE.
    void loadStandardConfig() noexcept;

    /// maybe re-implemented for some special providers which
    /// has persistent data like cache. Example - Mrpe providers
    virtual void loadConfig() {}
    int timeout() const noexcept { return timeout_; }
    virtual void registerCommandLine(const std::string &command_line);

    void registerOwner(cma::srv::ServiceProcessor *sp) noexcept;

    /// maybe re-implemented for some special providers which
    /// has persistent data like cache. Example - Plugin providers
    virtual void preStart() {}
    uint64_t errorCount() const noexcept { return error_count_; }
    uint64_t resetError() noexcept { return error_count_.exchange(0); }

    char separator() const noexcept { return separator_; }

    void stopWatchStart() { sw_.start(); }
    uint64_t stopWatchStop() { return sw_.stop(); }

    bool headerless() const noexcept { return headerless_; }
    bool enabled() const noexcept { return enabled_; }

protected:
    wtools::StopWatch sw_;
    // conditionally(depending from the name of section) sets delay after error
    void setupDelayOnFail() noexcept;

    void setHeaderless() noexcept { headerless_ = true; }

    /// stop section from rerunning during time defined in setupDelayOnFail
    /// usually related to the openhardware or maybe WMI monitor
    void disableSectionTemporary();

    bool sendGatheredData(const std::string &command_line);
    virtual std::string makeHeader(
        std::string_view section_name) const noexcept {
        return section::MakeHeader(section_name == section::kUseEmbeddedName
                                       ? std::string_view(uniq_name_)
                                       : section_name,
                                   separator_);
    }
    virtual std::string makeBody() = 0;

    const std::string uniq_name_;
    carrier::CoreCarrier carrier_;
    void setTimeout(int seconds) noexcept { timeout_ = seconds; }

    std::chrono::time_point<std::chrono::steady_clock> allowed_from_time_;

    /// this value may be set when we have problems with
    /// obtaining data. Next try will be set from
    /// now + delay_on_fail_ if delay_on_fail_ is not 0
    /// check ToggleIf in legacy Agent
    std::chrono::seconds delay_on_fail_{0};

    uint64_t registerError() noexcept { return error_count_.fetch_add(1); }
    srv::ServiceProcessor *getHostSp() const noexcept { return host_sp_; }

private:
    int timeout_{0};
    bool enabled_{true};
    bool headerless_{false};  // if true no makeHeader call
    std::string ip_;
    char separator_;
    std::atomic<uint64_t> error_count_{0};
    srv::ServiceProcessor *host_sp_{nullptr};
};

class Synchronous : public Basic {
public:
    explicit Synchronous(std::string_view name) noexcept : Basic(name) {}
    Synchronous(std::string_view name, char separator) noexcept
        : Basic(name, separator) {}
    ~Synchronous() override = default;

    bool startExecution(
        const std::string &internal_port,  // format "type:value
        const std::string &command_line    // format "id name whatever"
        ) override;
    bool stop(bool /*wait*/) noexcept override { return true; }
};

class Asynchronous : public Basic {
public:
    explicit Asynchronous(std::string_view name) noexcept : Basic(name) {}
    Asynchronous(std::string_view name, char separator) noexcept
        : Basic(name, separator) {}
    ~Asynchronous() override = default;

    bool startExecution(
        const std::string &internal_port,  // format "type:value"
        const std::string &command_line    // format "id name whatever"
        ) override;

    bool stop(bool wait) override;

protected:
    void threadProc(const std::string &internal_port,
                    const std::string &command_line,
                    std::chrono::milliseconds period);

private:
    std::thread thread_;

    std::condition_variable stop_thread_;
    mutable std::mutex lock_stopper_;
    bool stop_requested_{false};
};

}  // namespace cma::provider

#endif  // P_INTERNAL_H
