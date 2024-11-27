// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebCore_h
#define NebCore_h

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/Metric.h"
#include "livestatus/Store.h"
#include "livestatus/Triggers.h"
#include "livestatus/User.h"
#include "neb/nagios.h"

class Comment;
class Downtime;
enum class Encoding;
class InputBuffer;
class Logger;
class OutputBuffer;

struct NagiosLimits {
    size_t _max_cached_messages{500000};
    size_t _max_lines_per_logfile{1000000};
    size_t _max_response_size{size_t{100} * 1024 * 1024};
};

struct NagiosAuthorization {
    ServiceAuthorization _service{ServiceAuthorization::loose};
    GroupAuthorization _group{GroupAuthorization::strict};
};

struct NagiosPathConfig {
    std::filesystem::path log_file;
    std::filesystem::path crash_reports_directory;
    std::filesystem::path license_usage_history_file;
    std::filesystem::path inventory_directory;
    std::filesystem::path structured_status_directory;
    std::filesystem::path robotmk_html_log_directory;
    std::filesystem::path logwatch_directory;
    std::filesystem::path prediction_directory;
    std::filesystem::path event_console_status_socket;
    std::filesystem::path state_file_created_file;
    std::filesystem::path licensed_state_file;
    std::filesystem::path livestatus_socket;
    std::filesystem::path history_file;
    std::filesystem::path history_archive_directory;
    std::filesystem::path rrd_multiple_directory;
    std::filesystem::path rrdcached_socket;
};

class ExternalCommand {
public:
    explicit ExternalCommand(const std::string &str);
    [[nodiscard]] ExternalCommand withName(const std::string &name) const;
    [[nodiscard]] std::string name() const { return _name; }
    [[nodiscard]] std::string arguments() const { return _arguments; }
    [[nodiscard]] std::string str() const;
    [[nodiscard]] std::vector<std::string> args() const;

private:
    std::string _prefix;  // including brackets and space
    std::string _name;
    std::string _arguments;

    ExternalCommand(std::string prefix, std::string name, std::string arguments)
        : _prefix(std::move(prefix))
        , _name(std::move(name))
        , _arguments(std::move(arguments)) {}
};

class NebCore : public ICore {
public:
    NebCore(std::map<unsigned long, std::unique_ptr<Downtime>> &downtimes,
            std::map<unsigned long, std::unique_ptr<Comment>> &comments,
            NagiosPathConfig paths, const NagiosLimits &limits,
            NagiosAuthorization authorization, Encoding data_encoding,
            std::string edition,
            std::chrono::system_clock::time_point state_file_created);
    void dump_infos() const;

    const IHost *ihost(const ::host *handle) const;
    const IHostGroup *ihostgroup(const ::hostgroup *handle) const;
    const IService *iservice(const ::service *handle) const;
    const IServiceGroup *iservicegroup(const ::servicegroup *handle) const;
    const IContactGroup *icontactgroup(const ::contactgroup *handle) const;

    [[nodiscard]] const IHost *find_host(
        const std::string &name) const override;
    [[nodiscard]] const IHostGroup *find_hostgroup(
        const std::string &name) const override;
    [[nodiscard]] const IHost *getHostByDesignation(
        const std::string &designation) const override;
    bool all_of_hosts(
        const std::function<bool(const IHost &)> &pred) const override;
    bool all_of_services(
        const std::function<bool(const IService &)> &pred) const override;

    [[nodiscard]] const IService *find_service(
        const std::string &host_name,
        const std::string &service_description) const override;
    [[nodiscard]] const IServiceGroup *find_servicegroup(
        const std::string &name) const override;
    [[nodiscard]] const IContactGroup *find_contactgroup(
        const std::string &name) const override;

    [[nodiscard]] const IContact *find_contact(
        const std::string &name) const override;
    bool all_of_contacts(
        const std::function<bool(const IContact &)> &pred) const override;

    [[nodiscard]] std::unique_ptr<const User> find_user(
        const std::string &name) const override;

    [[nodiscard]] std::chrono::system_clock::time_point last_logfile_rotation()
        const override;
    [[nodiscard]] std::chrono::system_clock::time_point last_config_change()
        const override;
    [[nodiscard]] size_t maxLinesPerLogFile() const override;

    [[nodiscard]] Command find_command(const std::string &name) const override;
    [[nodiscard]] std::vector<Command> commands() const override;

    [[nodiscard]] std::vector<std::unique_ptr<const IComment>>
    comments_unlocked(const IHost &hst) const override;
    [[nodiscard]] std::vector<std::unique_ptr<const IComment>> comments(
        const IHost &hst) const override;
    [[nodiscard]] std::vector<std::unique_ptr<const IComment>>
    comments_unlocked(const IService &svc) const override;
    [[nodiscard]] std::vector<std::unique_ptr<const IComment>> comments(
        const IService &svc) const override;
    [[nodiscard]] bool all_of_comments(
        const std::function<bool(const IComment &)> &pred) const override;

    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>>
    downtimes_unlocked(const IHost &hst) const override;
    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>> downtimes(
        const IHost &hst) const override;
    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>>
    downtimes_unlocked(const IService &svc) const override;
    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>> downtimes(
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

    [[nodiscard]] bool mkeventdEnabled() const override;

    [[nodiscard]] int32_t pid() const override;
    [[nodiscard]] std::unique_ptr<const IGlobalFlags> globalFlags()
        const override;
    [[nodiscard]] std::unique_ptr<const IPaths> paths() const override;
    [[nodiscard]] std::chrono::system_clock::time_point programStartTime()
        const override;
    [[nodiscard]] std::chrono::system_clock::time_point lastCommandCheckTime()
        const override;
    [[nodiscard]] int32_t intervalLength() const override;
    [[nodiscard]] int32_t maxLongOutputSize() const override;
    [[nodiscard]] int32_t numHosts() const override;
    [[nodiscard]] int32_t numServices() const override;
    [[nodiscard]] std::string programVersion() const override;
    [[nodiscard]] std::string edition() const override;

    [[nodiscard]] int32_t externalCommandBufferSlots() const override;
    [[nodiscard]] int32_t externalCommandBufferUsage() const override;
    [[nodiscard]] int32_t externalCommandBufferMax() const override;

    [[nodiscard]] int32_t livestatusActiveConnectionsNum() const override;
    [[nodiscard]] std::string livestatusVersion() const override;
    [[nodiscard]] int32_t livestatusQueuedConnectionsNum() const override;
    [[nodiscard]] int32_t livestatusThreadsNum() const override;
    [[nodiscard]] double livestatusUsage() const override;

    [[nodiscard]] double averageLatencyGeneric() const override;
    [[nodiscard]] double averageLatencyRealTime() const override;
    [[nodiscard]] double averageLatencyFetcher() const override;
    [[nodiscard]] double averageLatencyChecker() const override;

    [[nodiscard]] double helperUsageGeneric() const override;
    [[nodiscard]] double helperUsageRealTime() const override;
    [[nodiscard]] double helperUsageFetcher() const override;
    [[nodiscard]] double helperUsageChecker() const override;

    [[nodiscard]] bool hasEventHandlers() const override;

    [[nodiscard]] double averageRunnableJobsFetcher() const override;
    [[nodiscard]] double averageRunnableJobsChecker() const override;

    [[nodiscard]] std::chrono::system_clock::time_point stateFileCreatedTime()
        const override;

    [[nodiscard]] Encoding dataEncoding() const override;
    [[nodiscard]] size_t maxResponseSize() const override;
    [[nodiscard]] size_t maxCachedMessages() const override;

    [[nodiscard]] Logger *loggerCore() const override;
    [[nodiscard]] Logger *loggerLivestatus() const override;
    [[nodiscard]] Logger *loggerRRD() const override;

    Triggers &triggers() override;

    [[nodiscard]] size_t numQueuedNotifications() const override;
    [[nodiscard]] size_t numQueuedAlerts() const override;
    [[nodiscard]] size_t numCachedLogMessages() override;
    [[nodiscard]] bool isPnpGraphPresent(const IHost &h) const override;
    [[nodiscard]] bool isPnpGraphPresent(const IService &s) const override;
    [[nodiscard]] std::vector<std::string> metrics(
        const IHost &h) const override;
    [[nodiscard]] std::vector<std::string> metrics(
        const IService &s) const override;

    [[nodiscard]] MetricLocation metricLocation(
        const std::string &host_name, const std::string &service_description,
        const Metric::Name &var) const override;
    [[nodiscard]] bool pnp4nagiosEnabled() const override;

    // specific for NebCore
    bool answerRequest(InputBuffer &input, OutputBuffer &output);
    std::map<unsigned long, std::unique_ptr<Downtime>> &_downtimes;
    std::map<unsigned long, std::unique_ptr<Comment>> &_comments;

private:
    Logger *_logger;
    const NagiosPathConfig _paths;
    const NagiosLimits _limits;
    const NagiosAuthorization _authorization;
    Encoding _data_encoding;
    std::string edition_;
    std::chrono::system_clock::time_point state_file_created_;
    Store _store;
    std::unordered_map<const ::host *, std::unique_ptr<IHost>>
        ihosts_by_handle_;
    std::unordered_map<const ::hostgroup *, std::unique_ptr<IHostGroup>>
        ihostgroups_by_handle_;
    // host is never nullptr
    std::unordered_map<std::string, ::host *> _hosts_by_designation;

    std::unordered_map<const ::service *, std::unique_ptr<IService>>
        iservices_by_handle_;
    std::unordered_map<const ::servicegroup *, std::unique_ptr<IServiceGroup>>
        iservicegroups_by_handle_;
    // host is never nullptr

    std::unordered_map<const ::contact *, std::unique_ptr<IContact>>
        icontacts_by_handle_;
    std::unordered_map<const ::contactgroup *, std::unique_ptr<IContactGroup>>
        icontactgroups_by_handle_;
    Triggers _triggers;

    // Nagios is not thread-safe, so this mutex protects calls to
    // process_external_command1 / submit_external_command.
    std::mutex _command_mutex;

    // TODO(sp): Avoid the suppression below.
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
    void *implInternal() const override { return const_cast<NebCore *>(this); }

    void logRequest(const std::string &line,
                    const std::vector<std::string> &lines);
    bool handleGet(InputBuffer &input, OutputBuffer &output,
                   const std::string &line, const std::string &table_name);
    void answerCommandRequest(const ExternalCommand &command);
    void answerCommandMkLogwatchAcknowledge(const ExternalCommand &command);
    void answerCommandDelCrashReport(const ExternalCommand &command);
    void answerCommandEventConsole(const std::string &command);
    void answerCommandNagios(const ExternalCommand &command);
};

Attributes CustomAttributes(const customvariablesmember *first,
                            AttributeKind kind);

std::optional<std::string> findCustomAttributeValue(
    const customvariablesmember *first, AttributeKind kind,
    const std::string &key);

#endif  // NebCore_h
