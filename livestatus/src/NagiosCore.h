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
#include <string>
#include <unordered_map>
#include <vector>

#include "DowntimeOrComment.h"  // IWYU pragma: keep
#include "Metric.h"
#include "MonitoringCore.h"
#include "Store.h"
#include "Triggers.h"
#include "auth.h"
#include "contact_fwd.h"
#include "nagios.h"
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

    Host *find_host(const std::string &name) override;
    host *getHostByDesignation(const std::string &designation) override;
    Service *find_service(const std::string &host_name,
                          const std::string &service_description) override;
    ContactGroup *find_contactgroup(const std::string &name) override;

    const Contact *find_contact(const std::string &name) override;
    bool is_contact_member_of_contactgroup(const ContactGroup *group,
                                           const Contact *contact) override;

    std::chrono::system_clock::time_point last_logfile_rotation() override;
    std::chrono::system_clock::time_point last_config_change() override;
    size_t maxLinesPerLogFile() const override;

    Command find_command(const std::string &name) const override;
    std::vector<Command> commands() const override;

    std::vector<DowntimeData> downtimes(const Host *host) const override;
    std::vector<DowntimeData> downtimes(const Service *service) const override;
    std::vector<CommentData> comments(const Host *host) const override;
    std::vector<CommentData> comments(const Service *service) const override;

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

    ServiceAuthorization serviceAuthorization() const override;
    GroupAuthorization groupAuthorization() const override;

    Logger *loggerLivestatus() override;
    Logger *loggerRRD() override;

    Triggers &triggers() override;

    size_t numQueuedNotifications() override;
    size_t numQueuedAlerts() override;
    size_t numCachedLogMessages() override;

    Attributes customAttributes(const void *holder,
                                AttributeKind kind) const override;

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
    std::unordered_map<std::string, host *> _hosts_by_designation;
    Triggers _triggers;

    void *implInternal() const override {
        return const_cast<NagiosCore *>(this);
    }

    static const Contact *fromImpl(const contact *c) {
        return reinterpret_cast<const Contact *>(c);
    }
    static const contact *toImpl(const Contact *c) {
        return reinterpret_cast<const contact *>(c);
    }

    static ContactGroup *fromImpl(contactgroup *g) {
        return reinterpret_cast<ContactGroup *>(g);
    }
    static const contactgroup *toImpl(const ContactGroup *g) {
        return reinterpret_cast<const contactgroup *>(g);
    }

    static Host *fromImpl(host *h) { return reinterpret_cast<Host *>(h); }
    static const host *toImpl(const Host *h) {
        return reinterpret_cast<const host *>(h);
    }

    static Service *fromImpl(service *s) {
        return reinterpret_cast<Service *>(s);
    }
    static const service *toImpl(const Service *s) {
        return reinterpret_cast<const service *>(s);
    }

    std::vector<DowntimeData> downtimes_for_object(const ::host *h,
                                                   const ::service *s) const;

    std::vector<CommentData> comments_for_object(const ::host *h,
                                                 const ::service *s) const;
};

#endif  // NagiosCore_h
