// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DummyMonitoringCore_h
#define DummyMonitoringCore_h

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

#include "livestatus/ICore.h"
#include "livestatus/Interface.h"  // IWYU pragma: keep
#include "livestatus/Logger.h"
#include "livestatus/Metric.h"
#include "livestatus/Triggers.h"
#include "livestatus/User.h"  // IWYU pragma: keep

class DummyMonitoringCore : public ICore {
    [[nodiscard]] const IHost *find_host(
        const std::string & /*name*/) const override {
        return nullptr;
    }
    [[nodiscard]] const IHostGroup *find_hostgroup(
        const std::string & /* name */) const override {
        return nullptr;
    }
    [[nodiscard]] const IHost *getHostByDesignation(
        const std::string & /*designation*/) const override {
        return {};
    }
    bool all_of_hosts(
        const std::function<bool(const IHost &)> & /*pred*/) const override {
        return true;
    }
    bool all_of_services(
        const std::function<bool(const IService &)> & /*pred*/) const override {
        return true;
    }
    [[nodiscard]] const IService *find_service(
        const std::string & /*host_name*/,
        const std::string & /*service_description*/) const override {
        return {};
    }
    [[nodiscard]] const IContactGroup *find_contactgroup(
        const std::string & /*name*/) const override {
        return {};
    }

    [[nodiscard]] const IServiceGroup *find_servicegroup(
        const std::string & /*name*/) const override {
        return nullptr;
    }

    [[nodiscard]] const IContact *find_contact(
        const std::string & /*name*/) const override {
        return {};
    }
    bool all_of_contacts(
        const std::function<bool(const IContact &)> & /*pred*/) const override {
        return true;
    }
    [[nodiscard]] std::unique_ptr<const User> find_user(
        const std::string & /*name*/) const override {
        return {};
    }

    [[nodiscard]] std::chrono::system_clock::time_point last_logfile_rotation()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_config_change()
        const override {
        return {};
    }
    [[nodiscard]] size_t maxLinesPerLogFile() const override { return {}; }

    [[nodiscard]] Command find_command(
        const std::string & /*name*/) const override {
        return {};
    }
    [[nodiscard]] std::vector<Command> commands() const override { return {}; }

    [[nodiscard]] std::vector<std::unique_ptr<const IComment>>
    comments_unlocked(const IHost & /*host*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IComment>> comments(
        const IHost & /*host*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IComment>>
    comments_unlocked(const IService & /*service*/) const override {
        return {};
    }
    [[nodiscard]] std::vector<std::unique_ptr<const IComment>> comments(
        const IService & /*service*/) const override {
        return {};
    }

    bool all_of_comments(
        const std::function<bool(const IComment &)> & /*pred*/) const override {
        return true;
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>>
    downtimes_unlocked(const IHost & /*host*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>> downtimes(
        const IHost & /*host*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>>
    downtimes_unlocked(const IService & /*service*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>> downtimes(
        const IService & /*service*/) const override {
        return {};
    }

    bool all_of_downtimes(const std::function<bool(const IDowntime &)>
                              & /*pred*/) const override {
        return true;
    }

    bool all_of_timeperiods(const std::function<bool(const ITimeperiod &)>
                                & /*pred*/) const override {
        return true;
    }

    bool all_of_contact_groups(const std::function<bool(const IContactGroup &)>
                                   & /* f */) const override {
        return {};
    }

    bool all_of_host_groups(const std::function<bool(const IHostGroup &)>
                                & /* f */) const override {
        return {};
    }

    bool all_of_service_groups(const std::function<bool(const IServiceGroup &)>
                                   & /* f */) const override {
        return {};
    }

    [[nodiscard]] bool mkeventdEnabled() const override { return {}; }

    [[nodiscard]] std::unique_ptr<const IPaths> paths() const override {
        return {};
    }
    [[nodiscard]] int32_t pid() const override { return {}; }
    [[nodiscard]] std::unique_ptr<const IGlobalFlags> globalFlags()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point programStartTime()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point lastCommandCheckTime()
        const override {
        return {};
    }
    [[nodiscard]] int32_t intervalLength() const override { return {}; }
    [[nodiscard]] int32_t maxLongOutputSize() const override { return {}; }
    [[nodiscard]] int32_t numHosts() const override { return {}; }
    [[nodiscard]] int32_t numServices() const override { return {}; }
    [[nodiscard]] std::string programVersion() const override { return {}; }
    [[nodiscard]] std::string edition() const override { return {}; }

    [[nodiscard]] int32_t externalCommandBufferSlots() const override {
        return {};
    }
    [[nodiscard]] int32_t externalCommandBufferUsage() const override {
        return {};
    }
    [[nodiscard]] int32_t externalCommandBufferMax() const override {
        return {};
    }

    [[nodiscard]] int32_t livestatusActiveConnectionsNum() const override {
        return {};
    }
    [[nodiscard]] std::string livestatusVersion() const override { return {}; }
    [[nodiscard]] int32_t livestatusQueuedConnectionsNum() const override {
        return {};
    }
    [[nodiscard]] int32_t livestatusThreadsNum() const override { return {}; }
    [[nodiscard]] double livestatusUsage() const override { return {}; }

    [[nodiscard]] double averageLatencyGeneric() const override { return {}; }
    [[nodiscard]] double averageLatencyChecker() const override { return {}; }
    [[nodiscard]] double averageLatencyFetcher() const override { return {}; }
    [[nodiscard]] double averageLatencyRealTime() const override { return {}; }

    [[nodiscard]] double helperUsageGeneric() const override { return {}; }
    [[nodiscard]] double helperUsageChecker() const override { return {}; }
    [[nodiscard]] double helperUsageFetcher() const override { return {}; }
    [[nodiscard]] double helperUsageRealTime() const override { return {}; }

    [[nodiscard]] bool hasEventHandlers() const override { return {}; }

    [[nodiscard]] double averageRunnableJobsFetcher() const override {
        return {};
    }
    [[nodiscard]] double averageRunnableJobsChecker() const override {
        return {};
    }

    [[nodiscard]] std::chrono::system_clock::time_point stateFileCreatedTime()
        const override {
        return {};
    }

    [[nodiscard]] std::vector<std::string> metrics(
        const IHost & /*h*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::string> metrics(
        const IService & /*s*/) const override {
        return {};
    }

    [[nodiscard]] bool isPnpGraphPresent(const IHost & /* h */) const override {
        return {};
    }

    [[nodiscard]] bool isPnpGraphPresent(
        const IService & /* s */) const override {
        return {};
    }

    [[nodiscard]] Encoding dataEncoding() const override { return {}; }
    [[nodiscard]] size_t maxResponseSize() const override { return {}; }
    [[nodiscard]] size_t maxCachedMessages() const override { return {}; }

    [[nodiscard]] Logger *loggerCore() const override {
        return Logger::getLogger("test");
    }
    [[nodiscard]] Logger *loggerLivestatus() const override { return {}; }
    [[nodiscard]] Logger *loggerRRD() const override { return {}; }

    Triggers &triggers() override { return triggers_; }
    const Triggers &triggers() const override { return triggers_; }

    [[nodiscard]] size_t numQueuedNotifications() const override { return {}; }
    [[nodiscard]] size_t numQueuedAlerts() const override { return {}; }
    [[nodiscard]] size_t numCachedLogMessages() override { return {}; }

    [[nodiscard]] MetricLocation metricLocation(
        const std::string & /*host_name*/,
        const std::string & /*service_description*/,
        const Metric::Name & /*var*/) const override {
        return {};
    }
    [[nodiscard]] bool pnp4nagiosEnabled() const override { return {}; }
    [[nodiscard]] bool isShuttingDown() const override { return {}; }

private:
    Triggers triggers_;
};

#endif  // DummyMonitoringCore_h
