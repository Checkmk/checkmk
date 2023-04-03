// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NagiosCore.h"

#include <algorithm>
#include <atomic>
#include <cstdlib>
#include <memory>
#include <utility>

#include "Comment.h"
#include "NebComment.h"
#include "NebContact.h"
#include "NebContactGroup.h"
#include "NebDowntime.h"
#include "NebGlobalFlags.h"
#include "NebHost.h"
#include "NebHostGroup.h"
#include "NebPaths.h"
#include "NebService.h"
#include "NebServiceGroup.h"
#include "NebTimeperiod.h"
#include "livestatus/Attributes.h"
#include "livestatus/Average.h"
#include "livestatus/Interface.h"
#include "livestatus/Logger.h"
#include "livestatus/PnpUtils.h"
#include "livestatus/StringUtils.h"

// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int g_num_hosts;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int g_num_services;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern bool g_any_event_handler_enabled;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern double g_average_active_latency;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern Average g_avg_livestatus_usage;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int g_livestatus_threads;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern int g_num_queued_connections;
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern std::atomic_int32_t g_livestatus_active_connections;

NagiosCore::NagiosCore(
    std::map<unsigned long, std::unique_ptr<Downtime>> &downtimes,
    std::map<unsigned long, std::unique_ptr<Comment>> &comments,
    NagiosPathConfig paths, const NagiosLimits &limits,
    NagiosAuthorization authorization, Encoding data_encoding)
    : _downtimes{downtimes}
    , _comments{comments}
    , _logger_livestatus(Logger::getLogger("cmk.livestatus"))
    , _paths(std::move(paths))
    , _limits(limits)
    , _authorization(authorization)
    , _data_encoding(data_encoding)
    , _store(this) {
    for (host *hst = host_list; hst != nullptr; hst = hst->next) {
        if (const char *address = hst->address) {
            _hosts_by_designation[mk::unsafe_tolower(address)] = hst;
        }
        if (const char *alias = hst->alias) {
            _hosts_by_designation[mk::unsafe_tolower(alias)] = hst;
        }
        _hosts_by_designation[mk::unsafe_tolower(hst->name)] = hst;
    }
}

std::unique_ptr<const IHost> NagiosCore::find_host(const std::string &name) {
    // Older Nagios headers are not const-correct... :-P
    const auto *host = ::find_host(const_cast<char *>(name.c_str()));
    return host == nullptr ? nullptr : std::make_unique<NebHost>(*host);
}

bool NagiosCore::all_of_hosts(
    const std::function<bool(const IHost &)> &pred) const {
    for (const auto *hst = host_list; hst != nullptr; hst = hst->next) {
        if (!pred(NebHost{*hst})) {
            return false;
        }
    }
    return true;
}

std::unique_ptr<const IHost> NagiosCore::getHostByDesignation(
    const std::string &designation) {
    auto it = _hosts_by_designation.find(mk::unsafe_tolower(designation));
    return it == _hosts_by_designation.end()
               ? nullptr
               : std::make_unique<NebHost>(*it->second);
}

std::unique_ptr<const IService> NagiosCore::find_service(
    const std::string &host_name, const std::string &service_description) {
    // Older Nagios headers are not const-correct... :-P
    const auto *svc =
        ::find_service(const_cast<char *>(host_name.c_str()),
                       const_cast<char *>(service_description.c_str()));
    return svc == nullptr ? nullptr : std::make_unique<NebService>(*svc);
}

std::unique_ptr<const IContactGroup> NagiosCore::find_contactgroup(
    const std::string &name) {
    return std::make_unique<NebContactGroup>(name);
}

std::unique_ptr<const IServiceGroup> NagiosCore::find_servicegroup(
    const std::string &name) {
    const auto *group = ::find_servicegroup(const_cast<char *>(name.c_str()));
    return group == nullptr ? nullptr
                            : std::make_unique<NebServiceGroup>(*group);
}

std::unique_ptr<const IContact> NagiosCore::find_contact(
    const std::string &name) const {
    // Older Nagios headers are not const-correct... :-P
    const auto *c = ::find_contact(const_cast<char *>(name.c_str()));
    return c == nullptr ? nullptr : std::make_unique<NebContact>(*c);
}

bool NagiosCore::all_of_contacts(
    const std::function<bool(const IContact &)> &pred) const {
    for (const ::contact *ctc = contact_list; ctc != nullptr; ctc = ctc->next) {
        if (!pred(NebContact{*ctc})) {
            return false;
        }
    }
    return true;
}

std::unique_ptr<User> NagiosCore::find_user(const std::string &name) {
    // Older Nagios headers are not const-correct... :-P
    if (const auto *ctc = ::find_contact(const_cast<char *>(name.c_str()))) {
        return std::make_unique<AuthUser>(
            std::make_unique<NebContact>(*ctc), _authorization._service,
            _authorization._group, [](const std::string &name) {
                return std::make_unique<NebContactGroup>(name);
            });
    }
    return std::make_unique<UnknownUser>();
}

std::chrono::system_clock::time_point NagiosCore::last_logfile_rotation()
    const {
    // TODO(sp) We should better listen to NEBCALLBACK_PROGRAM_STATUS_DATA
    // instead of this 'extern' hack...
    return std::chrono::system_clock::from_time_t(last_log_rotation);
}

std::chrono::system_clock::time_point NagiosCore::last_config_change() const {
    // NOTE: Nagios doesn't reload, it restarts for config changes.
    return std::chrono::system_clock::from_time_t(program_start);
}

size_t NagiosCore::maxLinesPerLogFile() const {
    return _limits._max_lines_per_logfile;
}

Command NagiosCore::find_command(const std::string &name) const {
    // Older Nagios headers are not const-correct... :-P
    if (command *cmd = ::find_command(const_cast<char *>(name.c_str()))) {
        return Command{._name = cmd->name, ._command_line = cmd->command_line};
    }
    return Command{._name = "", ._command_line = ""};
}

std::vector<Command> NagiosCore::commands() const {
    std::vector<Command> commands;
    for (command *cmd = command_list; cmd != nullptr; cmd = cmd->next) {
        commands.push_back(
            Command{._name = cmd->name, ._command_line = cmd->command_line});
    }
    return commands;
}

std::vector<std::unique_ptr<const IComment>> NagiosCore::comments_unlocked(
    const IHost &hst) const {
    std::vector<std::unique_ptr<const IComment>> result;
    for (const auto &[id, co] : _comments) {
        if (co->_host == static_cast<const host *>(hst.handle()) &&
            co->_service == nullptr) {
            result.emplace_back(std::make_unique<NebComment>(*co));
        }
    }
    return result;
}

std::vector<std::unique_ptr<const IComment>> NagiosCore::comments(
    const IHost &hst) const {
    // TODO(sp): Do we need a mutex here?
    return comments_unlocked(hst);
}

std::vector<std::unique_ptr<const IComment>> NagiosCore::comments_unlocked(
    const IService &svc) const {
    std::vector<std::unique_ptr<const IComment>> result;
    for (const auto &[id, co] : _comments) {
        if (co->_host == static_cast<const service *>(svc.handle())->host_ptr &&
            co->_service == static_cast<const service *>(svc.handle())) {
            result.emplace_back(std::make_unique<NebComment>(*co));
        }
    }
    return result;
}

std::vector<std::unique_ptr<const IComment>> NagiosCore::comments(
    const IService &svc) const {
    // TODO(sp): Do we need a mutex here?
    return comments_unlocked(svc);
}

bool NagiosCore::all_of_comments(
    const std::function<bool(const IComment &)> &pred) const {
    // TODO(sp): Do we need a mutex here?
    return std::all_of(_comments.cbegin(), _comments.cend(),
                       [&pred](const auto &comment) {
                           return pred(NebComment{*comment.second});
                       });
}

std::vector<std::unique_ptr<const IDowntime>> NagiosCore::downtimes_unlocked(
    const IHost &hst) const {
    std::vector<std::unique_ptr<const IDowntime>> result;
    for (const auto &[id, dt] : _downtimes) {
        if (dt->_host == static_cast<const host *>(hst.handle()) &&
            dt->_service == nullptr) {
            result.emplace_back(std::make_unique<NebDowntime>(*dt));
        }
    }
    return result;
}

std::vector<std::unique_ptr<const IDowntime>> NagiosCore::downtimes(
    const IHost &hst) const {
    // TODO(sp): Do we need a mutex here?
    return downtimes_unlocked(hst);
}

std::vector<std::unique_ptr<const IDowntime>> NagiosCore::downtimes_unlocked(
    const IService &svc) const {
    std::vector<std::unique_ptr<const IDowntime>> result;
    for (const auto &[id, dt] : _downtimes) {
        if (dt->_host == static_cast<const service *>(svc.handle())->host_ptr &&
            dt->_service == static_cast<const service *>(svc.handle())) {
            result.emplace_back(std::make_unique<NebDowntime>(*dt));
        }
    }
    return result;
}

std::vector<std::unique_ptr<const IDowntime>> NagiosCore::downtimes(
    const IService &svc) const {
    // TODO(sp): Do we need a mutex here?
    return downtimes_unlocked(svc);
}

bool NagiosCore::all_of_downtimes(
    // TODO(sp): Do we need a mutex here?
    const std::function<bool(const IDowntime &)> &pred) const {
    return std::all_of(_downtimes.cbegin(), _downtimes.cend(),
                       [&pred](const auto &downtime) {
                           return pred(NebDowntime{*downtime.second});
                       });
}

bool NagiosCore::all_of_timeperiods(
    const std::function<bool(const ITimeperiod &)> &pred) const {
    // TODO(sp): Do we need a mutex here?
    for (const timeperiod *tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        if (!pred(NebTimeperiod{*tp})) {
            return false;
        }
    }
    return true;
}

bool NagiosCore::all_of_contact_groups(
    const std::function<bool(const IContactGroup &)> &pred) const {
    for (const auto *cg = contactgroup_list; cg != nullptr; cg = cg->next) {
        if (!pred(NebContactGroup{*cg})) {
            return false;
        }
    }
    return true;
}

bool NagiosCore::all_of_host_groups(
    const std::function<bool(const IHostGroup &)> &pred) const {
    for (const auto *hg = hostgroup_list; hg != nullptr; hg = hg->next) {
        if (!pred(NebHostGroup{*hg})) {
            return false;
        }
    }
    return true;
}

bool NagiosCore::all_of_service_groups(
    const std::function<bool(const IServiceGroup &)> &pred) const {
    for (const auto *sg = servicegroup_list; sg != nullptr; sg = sg->next) {
        if (!pred(NebServiceGroup{*sg})) {
            return false;
        }
    }
    return true;
}

bool NagiosCore::mkeventdEnabled() {
    if (const char *config_mkeventd = getenv("CONFIG_MKEVENTD")) {
        return config_mkeventd == std::string("on");
    }
    return false;
}

int32_t NagiosCore::pid() const { return nagios_pid; }

std::unique_ptr<const IGlobalFlags> NagiosCore::globalFlags() const {
    return std::make_unique<const NebGlobalFlags>();
}

std::unique_ptr<const IPaths> NagiosCore::paths() const {
    return std::make_unique<NebPaths>(_paths);
}

std::chrono::system_clock::time_point NagiosCore::programStartTime() const {
    return std::chrono::system_clock::from_time_t(program_start);
}
std::chrono::system_clock::time_point NagiosCore::lastCommandCheckTime() const {
    return std::chrono::system_clock::from_time_t(
        nagios_compat_last_command_check());
}
int32_t NagiosCore::intervalLength() const { return interval_length; }
int32_t NagiosCore::numHosts() const { return g_num_hosts; }
int32_t NagiosCore::numServices() const { return g_num_services; }
std::string NagiosCore::programVersion() const { return get_program_version(); }

int32_t NagiosCore::externalCommandBufferSlots() const {
    return nagios_compat_external_command_buffer_slots();
}
int32_t NagiosCore::externalCommandBufferUsage() const {
    return nagios_compat_external_command_buffer_items();
}
int32_t NagiosCore::externalCommandBufferMax() const {
    return nagios_compat_external_command_buffer_high();
}

int32_t NagiosCore::livestatusActiveConnectionsNum() const {
    return g_livestatus_active_connections.load();
}
std::string NagiosCore::livestatusVersion() const { return VERSION; }
int32_t NagiosCore::livestatusQueuedConnectionsNum() const {
    return g_num_queued_connections;
}
int32_t NagiosCore::livestatusThreadsNum() const {
    return g_livestatus_threads;
}
double NagiosCore::livestatusUsage() const {
    return g_avg_livestatus_usage.get();
}

double NagiosCore::averageLatencyGeneric() const {
    return g_average_active_latency;
}
double NagiosCore::averageLatencyRealTime() const { return 0.0; }
double NagiosCore::averageLatencyFetcher() const { return 0.0; }
double NagiosCore::averageLatencyChecker() const { return 0.0; }

double NagiosCore::helperUsageGeneric() const { return 0.0; }
double NagiosCore::helperUsageRealTime() const { return 0.0; }
double NagiosCore::helperUsageFetcher() const { return 0.0; }
double NagiosCore::helperUsageChecker() const { return 0.0; }

bool NagiosCore::hasEventHandlers() const {
    return g_any_event_handler_enabled;
}

bool NagiosCore::isTrialExpired(
    std::chrono::system_clock::time_point /*now*/) const {
    return false;
}

double NagiosCore::averageRunnableJobsFetcher() const { return 0.0; }
double NagiosCore::averageRunnableJobsChecker() const { return 0.0; }

std::chrono::system_clock::time_point NagiosCore::stateFileCreatedTime() const {
    return {};
}

Encoding NagiosCore::dataEncoding() { return _data_encoding; }
size_t NagiosCore::maxResponseSize() { return _limits._max_response_size; }
size_t NagiosCore::maxCachedMessages() { return _limits._max_cached_messages; }

Logger *NagiosCore::loggerCore() { return _logger_livestatus; }
Logger *NagiosCore::loggerLivestatus() { return _logger_livestatus; }
Logger *NagiosCore::loggerRRD() { return _logger_livestatus; }

Triggers &NagiosCore::triggers() { return _triggers; }

size_t NagiosCore::numQueuedNotifications() const { return 0; }
size_t NagiosCore::numQueuedAlerts() const { return 0; }

size_t NagiosCore::numCachedLogMessages() {
    return _store.numCachedLogMessages();
}

namespace {
// Nagios converts custom attribute names to uppercase, splits name/value at
// space, uses ';' as a comment character, is line-oriented, etc. etc. So we
// use a base16 encoding for names and values of tags, labels, and label
// sources, e.g. "48656C6C6F2C20776F726C6421" => "Hello, world!".
std::string b16decode(const std::string &hex) {
    auto len = hex.length() & ~1;
    std::string result;
    result.reserve(len / 2);
    for (size_t i = 0; i < len; i += 2) {
        result.push_back(strtol(hex.substr(i, 2).c_str(), nullptr, 16));
    }
    return result;
}
}  // namespace

Attributes CustomAttributes(const customvariablesmember *first,
                            AttributeKind kind) {
    Attributes attrs;
    for (const auto *cvm = first; cvm != nullptr; cvm = cvm->next) {
        auto [k, name] = to_attribute_kind(cvm->variable_name);
        if (k == kind) {
            const auto *value =
                cvm->variable_value == nullptr ? "" : cvm->variable_value;
            switch (kind) {
                case AttributeKind::custom_variables:
                    attrs.emplace(name, value);
                    break;
                case AttributeKind::tags:
                case AttributeKind::labels:
                case AttributeKind::label_sources:
                    attrs.emplace(b16decode(name), b16decode(value));
                    break;
            }
        }
    }
    return attrs;
}

// TODO(sp): Reduce copy-n-paste with function above.
std::optional<std::string> findCustomAttributeValue(
    const customvariablesmember *first, AttributeKind kind,
    const std::string &key) {
    for (const auto *cvm = first; cvm != nullptr; cvm = cvm->next) {
        auto [k, name] = to_attribute_kind(cvm->variable_name);
        if (k == kind) {
            const auto *value =
                cvm->variable_value == nullptr ? "" : cvm->variable_value;
            switch (kind) {
                case AttributeKind::custom_variables:
                    if (key == name) {
                        return value;
                    }
                    break;
                case AttributeKind::tags:
                case AttributeKind::labels:
                case AttributeKind::label_sources:
                    if (key == b16decode(name)) {
                        return b16decode(value);
                    }
                    break;
            }
        }
    }
    return {};
}

MetricLocation NagiosCore::metricLocation(
    const std::string &host_name, const std::string &service_description,
    const Metric::Name &var) const {
    return MetricLocation{
        paths()->rrd_multiple_directory() / host_name /
            pnp_cleanup(service_description + "_" +
                        Metric::MangledName(var).string() + ".rrd"),
        "1"};
}

bool NagiosCore::pnp4nagiosEnabled() const {
    return true;  // TODO(sp) ???
}

bool NagiosCore::answerRequest(InputBuffer &input, OutputBuffer &output) {
    return _store.answerRequest(input, output);
}
