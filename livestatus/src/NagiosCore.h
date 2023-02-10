// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NagiosCore_h
#define NagiosCore_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include "Downtime.h"  // IWYU pragma: keep
#include "Store.h"
#include "livestatus/Interface.h"
#include "livestatus/Metric.h"
#include "livestatus/MonitoringCore.h"
#include "livestatus/Renderer.h"
#include "livestatus/Triggers.h"
#include "livestatus/User.h"
#include "nagios.h"
class Comment;
class InputBuffer;
class Logger;
class OutputBuffer;

struct NagiosPaths {
    std::string _socket{"/usr/local/nagios/var/rw/live"};
    std::string _pnp;
    std::string _mk_inventory;
    std::string _structured_status;
    std::filesystem::path _robotmk_html_log_path;
    std::filesystem::path _crash_reports_path;
    std::filesystem::path _license_usage_history_path;
    std::string _mk_logwatch;
    std::string _logfile;
    std::string _mkeventd_socket;
    std::string _rrdcached_socket;

    void dump(Logger *logger) const;
};

struct NagiosLimits {
    size_t _max_cached_messages{500000};
    size_t _max_lines_per_logfile{1000000};
    size_t _max_response_size{size_t{100} * 1024 * 1024};
};

struct NagiosAuthorization {
    ServiceAuthorization _service{ServiceAuthorization::loose};
    GroupAuthorization _group{GroupAuthorization::strict};
};

class NagiosCore : public MonitoringCore {
public:
    NagiosCore(std::map<unsigned long, std::unique_ptr<Downtime>> &downtimes,
               std::map<unsigned long, std::unique_ptr<Comment>> &comments,
               NagiosPaths paths, const NagiosLimits &limits,
               NagiosAuthorization authorization, Encoding data_encoding);

    std::unique_ptr<const IHost> find_host(const std::string &name) override;
    std::unique_ptr<const IHost> getHostByDesignation(
        const std::string &designation) override;
    bool all_of_hosts(
        const std::function<bool(const IHost &)> &pred) const override;

    std::unique_ptr<const IService> find_service(
        const std::string &host_name,
        const std::string &service_description) override;
    std::unique_ptr<const IContactGroup> find_contactgroup(
        const std::string &name) override;
    std::unique_ptr<const IServiceGroup> find_servicegroup(
        const std::string &name) override;

    std::unique_ptr<const IContact> find_contact(
        const std::string &name) const override;
    bool all_of_contacts(
        const std::function<bool(const IContact &)> &pred) const override;

    std::unique_ptr<User> find_user(const std::string &name) override;

    std::chrono::system_clock::time_point last_logfile_rotation()
        const override;
    std::chrono::system_clock::time_point last_config_change() const override;
    size_t maxLinesPerLogFile() const override;

    Command find_command(const std::string &name) const override;
    std::vector<Command> commands() const override;

    std::vector<std::unique_ptr<const IComment>> comments(
        const IHost &hst) const override;
    std::vector<std::unique_ptr<const IComment>> comments(
        const IService &svc) const override;
    bool all_of_comments(
        const std::function<bool(const IComment &)> &pred) const override;

    std::vector<std::unique_ptr<const IDowntime>> downtimes(
        const IHost &hst) const override;
    std::vector<std::unique_ptr<const IDowntime>> downtimes(
        const IService &svc) const override;
    bool all_of_downtimes(
        const std::function<bool(const IDowntime &)> &pred) const override;

    bool all_of_timeperiods(
        const std::function<bool(const ITimeperiod &)> &pred) const override;

    bool all_of_contact_groups(
        const std::function<bool(const IContactGroup &)> &pred) const override;

    bool all_of_host_groups(
        const std::function<bool(const IHostGroup &)> &pred) const override;

    bool all_of_service_groups(
        const std::function<bool(const IServiceGroup &)> &pred) const override;

    bool mkeventdEnabled() override;

    std::filesystem::path mkeventdSocketPath() const override;
    std::filesystem::path mkLogwatchPath() const override;
    std::filesystem::path mkInventoryPath() const override;
    std::filesystem::path structuredStatusPath() const override;
    std::filesystem::path robotMkHtmlLogPath() const override;
    std::filesystem::path crashReportPath() const override;
    std::filesystem::path licenseUsageHistoryPath() const override;
    std::filesystem::path pnpPath() const override;
    std::filesystem::path historyFilePath() const override;
    std::filesystem::path logArchivePath() const override;
    std::filesystem::path rrdcachedSocketPath() const override;

    int32_t pid() const override;
    [[nodiscard]] GlobalFlags globalFlags() const override;
    std::chrono::system_clock::time_point programStartTime() const override;
    std::chrono::system_clock::time_point lastCommandCheckTime() const override;
    int32_t intervalLength() const override;
    int32_t numHosts() const override;
    int32_t numServices() const override;
    std::string programVersion() const override;

    int32_t externalCommandBufferSlots() const override;
    int32_t externalCommandBufferUsage() const override;
    int32_t externalCommandBufferMax() const override;

    int32_t livestatusActiveConnectionsNum() const override;
    std::string livestatusVersion() const override;
    int32_t livestatusQueuedConnectionsNum() const override;
    int32_t livestatusThreadsNum() const override;
    double livestatusUsage() const override;

    double averageLatencyGeneric() const override;
    double averageLatencyCmk() const override;
    double averageLatencyFetcher() const override;
    double averageLatencyRealTime() const override;

    double helperUsageGeneric() const override;
    double helperUsageCmk() const override;
    double helperUsageFetcher() const override;
    double helperUsageChecker() const override;
    double helperUsageRealTime() const override;

    bool hasEventHandlers() const override;

    bool isTrialExpired(
        std::chrono::system_clock::time_point now) const override;

    double averageRunnableJobsFetcher() const override;
    double averageRunnableJobsChecker() const override;

    std::chrono::system_clock::time_point stateFileCreatedTime() const override;

    Encoding dataEncoding() override;
    size_t maxResponseSize() override;
    size_t maxCachedMessages() override;

    Logger *loggerCore() override;
    Logger *loggerLivestatus() override;
    Logger *loggerRRD() override;

    Triggers &triggers() override;

    size_t numQueuedNotifications() override;
    size_t numQueuedAlerts() override;
    size_t numCachedLogMessages() override;

    MetricLocation metricLocation(const std::string &host_name,
                                  const std::string &service_description,
                                  const Metric::Name &var) const override;
    bool pnp4nagiosEnabled() const override;

    // specific for NagiosCore
    bool answerRequest(InputBuffer &input, OutputBuffer &output);
    std::map<unsigned long, std::unique_ptr<Downtime>> &_downtimes;
    std::map<unsigned long, std::unique_ptr<Comment>> &_comments;

private:
    Logger *_logger_livestatus;
    const NagiosPaths _paths;
    const NagiosLimits _limits;
    const NagiosAuthorization _authorization;
    Encoding _data_encoding;
    Store _store;
    // host is never nullptr
    std::unordered_map<std::string, host *> _hosts_by_designation;
    Triggers _triggers;

    void *implInternal() const override {
        return const_cast<NagiosCore *>(this);
    }
};

Attributes CustomAttributes(const customvariablesmember *first,
                            AttributeKind kind);

std::optional<std::string> findCustomAttributeValue(
    const customvariablesmember *first, AttributeKind kind,
    const std::string &key);

#endif  // NagiosCore_h
