// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NagiosCore_h
#define NagiosCore_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstddef>
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
#include "livestatus/Attributes.h"
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

class IComment;
class IContact;
class IContactGroup;
class IDowntime;
class IHost;
class IService;
class ITimeperiod;

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
    std::unique_ptr<const IService> find_service(
        const std::string &host_name,
        const std::string &service_description) override;
    std::unique_ptr<const IContactGroup> find_contactgroup(
        const std::string &name) override;
    std::unique_ptr<const IContact> find_contact(
        const std::string &name) override;
    std::unique_ptr<User> find_user(const std::string &name) override;

    std::chrono::system_clock::time_point last_logfile_rotation() override;
    std::chrono::system_clock::time_point last_config_change() override;
    size_t maxLinesPerLogFile() const override;

    Command find_command(const std::string &name) const override;
    std::vector<Command> commands() const override;

    std::vector<std::unique_ptr<const IComment>> comments(
        const IHost &hst) const override;
    std::vector<std::unique_ptr<const IComment>> comments(
        const IService &svc) const override;
    void forEachCommentUntil(
        const std::function<bool(const IComment &)> &f) const override;

    std::vector<std::unique_ptr<const IDowntime>> downtimes(
        const IHost &hst) const override;
    std::vector<std::unique_ptr<const IDowntime>> downtimes(
        const IService &svc) const override;
    void forEachDowntimeUntil(
        const std::function<bool(const IDowntime &)> &f) const override;

    void forEachLabelUntil(
        const std::function<bool(const std::string &name,
                                 const std::string &value)> &f) const override;

    void forEachTimeperiodUntil(
        const std::function<bool(const ITimeperiod &)> &f) const override;

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
