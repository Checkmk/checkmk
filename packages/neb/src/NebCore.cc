// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "neb/NebCore.h"

#include <algorithm>
#include <atomic>
#include <cstdlib>
#include <iterator>
#include <sstream>
#include <stdexcept>
#include <system_error>

#include "livestatus/Attributes.h"
#include "livestatus/Average.h"
#include "livestatus/CrashReport.h"
#include "livestatus/EventConsoleConnection.h"
#include "livestatus/InputBuffer.h"
#include "livestatus/Logger.h"
#include "livestatus/OutputBuffer.h"
#include "livestatus/PnpUtils.h"
#include "livestatus/StringUtils.h"
#include "livestatus/mk_logwatch.h"
#include "neb/CmkVersion.h"
#include "neb/Comment.h"
#include "neb/Downtime.h"
#include "neb/NebComment.h"
#include "neb/NebContact.h"
#include "neb/NebContactGroup.h"
#include "neb/NebDowntime.h"
#include "neb/NebGlobalFlags.h"
#include "neb/NebHost.h"
#include "neb/NebHostGroup.h"
#include "neb/NebPaths.h"
#include "neb/NebService.h"
#include "neb/NebServiceGroup.h"
#include "neb/NebTimeperiod.h"

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

ExternalCommand::ExternalCommand(const std::string &str) {
    constexpr int timestamp_len = 10;
    constexpr int prefix_len = timestamp_len + 3;
    if (str.size() <= prefix_len || str[0] != '[' ||
        str[prefix_len - 2] != ']' || str[prefix_len - 1] != ' ') {
        throw std::invalid_argument("malformed timestamp in command '" + str +
                                    "'");
    }
    auto semi = str.find(';', prefix_len);
    _prefix = str.substr(0, prefix_len);
    _name = str.substr(prefix_len, semi - prefix_len);
    _arguments = semi == std::string::npos ? "" : str.substr(semi);
}

ExternalCommand ExternalCommand::withName(const std::string &name) const {
    return {_prefix, name, _arguments};
}

std::string ExternalCommand::str() const {
    return _prefix + _name + _arguments;
}

std::vector<std::string> ExternalCommand::args() const {
    if (_arguments.empty()) {
        return {};
    }
    return mk::split(_arguments.substr(1), ';');
}

NebCore::NebCore(std::map<unsigned long, std::unique_ptr<Downtime>> &downtimes,
                 std::map<unsigned long, std::unique_ptr<Comment>> &comments,
                 NagiosPathConfig paths, const NagiosLimits &limits,
                 NagiosAuthorization authorization, Encoding data_encoding,
                 std::string edition,
                 std::chrono::system_clock::time_point state_file_created)
    : _downtimes{downtimes}
    , _comments{comments}
    , _logger(Logger::getLogger("cmk.livestatus"))
    , _paths(std::move(paths))
    , _limits(limits)
    , _authorization(authorization)
    , _data_encoding(data_encoding)
    , edition_{std::move(edition)}
    , state_file_created_{state_file_created}
    , _store(_logger) {
    for (::host *hst = host_list; hst != nullptr; hst = hst->next) {
        ihosts_by_handle_[hst] = std::make_unique<NebHost>(*hst, *this);
        if (const char *address = hst->address) {
            _hosts_by_designation[mk::unsafe_tolower(address)] = hst;
        }
        if (const char *alias = hst->alias) {
            _hosts_by_designation[mk::unsafe_tolower(alias)] = hst;
        }
        _hosts_by_designation[mk::unsafe_tolower(hst->name)] = hst;
    }

    for (::service *svc = service_list; svc != nullptr; svc = svc->next) {
        iservices_by_handle_[svc] = std::make_unique<NebService>(*svc, *this);
    }

    for (const auto *hg = hostgroup_list; hg != nullptr; hg = hg->next) {
        ihostgroups_by_handle_[hg] = std::make_unique<NebHostGroup>(*hg, *this);
    }

    for (const auto *sg = servicegroup_list; sg != nullptr; sg = sg->next) {
        iservicegroups_by_handle_[sg] =
            std::make_unique<NebServiceGroup>(*sg, *this);
    }

    for (const ::contact *ctc = contact_list; ctc != nullptr; ctc = ctc->next) {
        icontacts_by_handle_[ctc] = std::make_unique<NebContact>(*ctc);
    }

    for (const ::contactgroup *cg = contactgroup_list; cg != nullptr;
         cg = cg->next) {
        icontactgroups_by_handle_[cg] = std::make_unique<NebContactGroup>(*cg);
    }
}

void NebCore::dump_infos() const {
    Notice(_logger) << "created core abstraction with "
                    << ihosts_by_handle_.size() << " hosts, "
                    << ihostgroups_by_handle_.size() << " host groups, "
                    << iservices_by_handle_.size() << " services, "
                    << iservicegroups_by_handle_.size() << " service groups, "
                    << icontacts_by_handle_.size() << " contacts, "
                    << icontactgroups_by_handle_.size() << " contact groups";
}

const IHost *NebCore::ihost(const ::host *handle) const {
    auto it = ihosts_by_handle_.find(handle);
    return it == ihosts_by_handle_.end() ? nullptr : it->second.get();
}

const IHostGroup *NebCore::ihostgroup(const ::hostgroup *handle) const {
    auto it = ihostgroups_by_handle_.find(handle);
    return it == ihostgroups_by_handle_.end() ? nullptr : it->second.get();
}

const IHost *NebCore::find_host(const std::string &name) const {
    // Older Nagios headers are not const-correct... :-P
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
    const auto *handle = ::find_host(const_cast<char *>(name.c_str()));
    return handle == nullptr ? nullptr : ihost(handle);
}

const IHostGroup *NebCore::find_hostgroup(const std::string &name) const {
    // Older Nagios headers are not const-correct... :-P
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
    const auto *handle = ::find_hostgroup(const_cast<char *>(name.c_str()));
    return handle == nullptr ? nullptr : ihostgroup(handle);
}

bool NebCore::all_of_hosts(
    const std::function<bool(const IHost &)> &pred) const {
    return std::ranges::all_of(ihosts_by_handle_, [pred](const auto &entry) {
        return pred(*entry.second);
    });
}

bool NebCore::all_of_services(
    const std::function<bool(const IService &)> &pred) const {
    return std::ranges::all_of(iservices_by_handle_, [pred](const auto &entry) {
        return pred(*entry.second);
    });
}

const IHost *NebCore::getHostByDesignation(
    const std::string &designation) const {
    auto it = _hosts_by_designation.find(mk::unsafe_tolower(designation));
    return it == _hosts_by_designation.end() ? nullptr : ihost(it->second);
}

const IService *NebCore::iservice(const ::service *handle) const {
    auto it = iservices_by_handle_.find(handle);
    return it == iservices_by_handle_.end() ? nullptr : it->second.get();
}

const IServiceGroup *NebCore::iservicegroup(
    const ::servicegroup *handle) const {
    auto it = iservicegroups_by_handle_.find(handle);
    return it == iservicegroups_by_handle_.end() ? nullptr : it->second.get();
}

const IService *NebCore::find_service(
    const std::string &host_name,
    const std::string &service_description) const {
    const auto *handle = ::find_service(
        // Older Nagios headers are not const-correct... :-P
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
        const_cast<char *>(host_name.c_str()),
        // Older Nagios headers are not const-correct... :-P
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
        const_cast<char *>(service_description.c_str()));
    return handle == nullptr ? nullptr : iservice(handle);
}

const IContactGroup *NebCore::icontactgroup(
    const ::contactgroup *handle) const {
    auto it = icontactgroups_by_handle_.find(handle);
    return it == icontactgroups_by_handle_.end() ? nullptr : it->second.get();
}

const IContactGroup *NebCore::find_contactgroup(const std::string &name) const {
    // Older Nagios headers are not const-correct... :-P
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
    const auto *handle = ::find_contactgroup(const_cast<char *>(name.c_str()));
    return handle == nullptr ? nullptr : icontactgroup(handle);
}

const IServiceGroup *NebCore::find_servicegroup(const std::string &name) const {
    // Older Nagios headers are not const-correct... :-P
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
    const auto *handle = ::find_servicegroup(const_cast<char *>(name.c_str()));
    return handle == nullptr ? nullptr : iservicegroup(handle);
}

const IContact *NebCore::find_contact(const std::string &name) const {
    auto it = icontacts_by_handle_.find(
        // Older Nagios headers are not const-correct... :-P
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
        ::find_contact(const_cast<char *>(name.c_str())));
    return it == icontacts_by_handle_.end() ? nullptr : it->second.get();
}

bool NebCore::all_of_contacts(
    const std::function<bool(const IContact &)> &pred) const {
    return std::ranges::all_of(
        icontacts_by_handle_,
        [&pred](const auto &entry) { return pred(*entry.second); });
}

std::unique_ptr<const User> NebCore::find_user(const std::string &name) const {
    if (const auto *ctc = find_contact(name)) {
        return std::make_unique<AuthUser>(
            *ctc, _authorization._service, _authorization._group,
            [this](const auto &n) { return this->find_contactgroup(n); });
    }
    return std::make_unique<UnknownUser>();
}

std::chrono::system_clock::time_point NebCore::last_logfile_rotation() const {
    // TODO(sp) We should better listen to NEBCALLBACK_PROGRAM_STATUS_DATA
    // instead of this 'extern' hack...
    return std::chrono::system_clock::from_time_t(last_log_rotation);
}

std::chrono::system_clock::time_point NebCore::last_config_change() const {
    // NOTE: Nagios doesn't reload, it restarts for config changes.
    return std::chrono::system_clock::from_time_t(program_start);
}

size_t NebCore::maxLinesPerLogFile() const {
    return _limits._max_lines_per_logfile;
}

Command NebCore::find_command(const std::string &name) const {
    // Older Nagios headers are not const-correct... :-P
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
    if (command *cmd = ::find_command(const_cast<char *>(name.c_str()))) {
        return Command{._name = cmd->name, ._command_line = cmd->command_line};
    }
    return Command{._name = "", ._command_line = ""};
}

std::vector<Command> NebCore::commands() const {
    std::vector<Command> commands;
    for (command *cmd = command_list; cmd != nullptr; cmd = cmd->next) {
        commands.push_back(
            Command{._name = cmd->name, ._command_line = cmd->command_line});
    }
    return commands;
}

std::vector<std::unique_ptr<const IComment>> NebCore::comments_unlocked(
    const IHost &hst) const {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-static-cast-downcast)
    const auto &h = static_cast<const NebHost &>(hst).handle();
    std::vector<std::unique_ptr<const IComment>> result;
    for (const auto &[id, co] : _comments) {
        if (co->_host == &h && co->_service == nullptr) {
            result.emplace_back(
                std::make_unique<NebComment>(*co, hst, nullptr));
        }
    }
    return result;
}

std::vector<std::unique_ptr<const IComment>> NebCore::comments(
    const IHost &hst) const {
    // TODO(sp): Do we need a mutex here?
    return comments_unlocked(hst);
}

std::vector<std::unique_ptr<const IComment>> NebCore::comments_unlocked(
    const IService &svc) const {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-static-cast-downcast)
    const auto &s = static_cast<const NebService &>(svc).handle();
    std::vector<std::unique_ptr<const IComment>> result;
    for (const auto &[id, co] : _comments) {
        if (co->_host == s.host_ptr && co->_service == &s) {
            result.emplace_back(
                std::make_unique<NebComment>(*co, svc.host(), &svc));
        }
    }
    return result;
}

std::vector<std::unique_ptr<const IComment>> NebCore::comments(
    const IService &svc) const {
    // TODO(sp): Do we need a mutex here?
    return comments_unlocked(svc);
}

bool NebCore::all_of_comments(
    const std::function<bool(const IComment &)> &pred) const {
    // TODO(sp): Do we need a mutex here?
    return std::ranges::all_of(_comments, [this, &pred](const auto &comment) {
        return pred(NebComment{*comment.second, *ihost(comment.second->_host),
                               iservice(comment.second->_service)});
    });
}

std::vector<std::unique_ptr<const IDowntime>> NebCore::downtimes_unlocked(
    const IHost &hst) const {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-static-cast-downcast)
    const auto &h = static_cast<const NebHost &>(hst).handle();
    std::vector<std::unique_ptr<const IDowntime>> result;
    for (const auto &[id, dt] : _downtimes) {
        if (dt->_host == &h && dt->_service == nullptr) {
            result.emplace_back(
                std::make_unique<NebDowntime>(*dt, hst, nullptr));
        }
    }
    return result;
}

std::vector<std::unique_ptr<const IDowntime>> NebCore::downtimes(
    const IHost &hst) const {
    // TODO(sp): Do we need a mutex here?
    return downtimes_unlocked(hst);
}

std::vector<std::unique_ptr<const IDowntime>> NebCore::downtimes_unlocked(
    const IService &svc) const {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-static-cast-downcast)
    const auto &s = static_cast<const NebService &>(svc).handle();
    std::vector<std::unique_ptr<const IDowntime>> result;
    for (const auto &[id, dt] : _downtimes) {
        if (dt->_host == s.host_ptr && dt->_service == &s) {
            result.emplace_back(
                std::make_unique<NebDowntime>(*dt, svc.host(), &svc));
        }
    }
    return result;
}

std::vector<std::unique_ptr<const IDowntime>> NebCore::downtimes(
    const IService &svc) const {
    // TODO(sp): Do we need a mutex here?
    return downtimes_unlocked(svc);
}

bool NebCore::all_of_downtimes(
    // TODO(sp): Do we need a mutex here?
    const std::function<bool(const IDowntime &)> &pred) const {
    return std::ranges::all_of(_downtimes, [this, &pred](const auto &downtime) {
        return pred(NebDowntime{*downtime.second,
                                *ihost(downtime.second->_host),
                                iservice(downtime.second->_service)});
    });
}

bool NebCore::all_of_timeperiods(
    const std::function<bool(const ITimeperiod &)> &pred) const {
    // TODO(sp): Do we need a mutex here?
    for (const timeperiod *tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        if (!pred(NebTimeperiod{*tp})) {
            return false;
        }
    }
    return true;
}

bool NebCore::all_of_contact_groups(
    const std::function<bool(const IContactGroup &)> &pred) const {
    return std::ranges::all_of(
        icontactgroups_by_handle_,
        [&pred](const auto &entry) { return pred(*entry.second); });
}

bool NebCore::all_of_host_groups(
    const std::function<bool(const IHostGroup &)> &pred) const {
    return std::ranges::all_of(
        ihostgroups_by_handle_,
        [pred](const auto &entry) { return pred(*entry.second); });
}

bool NebCore::all_of_service_groups(
    const std::function<bool(const IServiceGroup &)> &pred) const {
    return std::ranges::all_of(
        iservicegroups_by_handle_,
        [pred](const auto &entry) { return pred(*entry.second); });
    return true;
}

bool NebCore::mkeventdEnabled() const {
    // NOLINTNEXTLINE(concurrency-mt-unsafe)
    if (const char *config_mkeventd = getenv("CONFIG_MKEVENTD")) {
        return config_mkeventd == std::string("on");
    }
    return false;
}

int32_t NebCore::pid() const { return nagios_pid; }

std::unique_ptr<const IGlobalFlags> NebCore::globalFlags() const {
    return std::make_unique<const NebGlobalFlags>();
}

std::unique_ptr<const IPaths> NebCore::paths() const {
    return std::make_unique<NebPaths>(_paths);
}

std::chrono::system_clock::time_point NebCore::programStartTime() const {
    return std::chrono::system_clock::from_time_t(program_start);
}
std::chrono::system_clock::time_point NebCore::lastCommandCheckTime() const {
    return std::chrono::system_clock::from_time_t(
        nagios_compat_last_command_check());
}
int32_t NebCore::intervalLength() const { return interval_length; }
int32_t NebCore::maxLongOutputSize() const { return 0; }
int32_t NebCore::numHosts() const { return g_num_hosts; }
int32_t NebCore::numServices() const { return g_num_services; }
std::string NebCore::programVersion() const { return get_program_version(); }
std::string NebCore::edition() const { return edition_; }

int32_t NebCore::externalCommandBufferSlots() const {
    return nagios_compat_external_command_buffer_slots();
}
int32_t NebCore::externalCommandBufferUsage() const {
    return nagios_compat_external_command_buffer_items();
}
int32_t NebCore::externalCommandBufferMax() const {
    return nagios_compat_external_command_buffer_high();
}

int32_t NebCore::livestatusActiveConnectionsNum() const {
    return g_livestatus_active_connections.load();
}
std::string NebCore::livestatusVersion() const { return cmk::version(); }
int32_t NebCore::livestatusQueuedConnectionsNum() const {
    return g_num_queued_connections;
}
int32_t NebCore::livestatusThreadsNum() const { return g_livestatus_threads; }
double NebCore::livestatusUsage() const { return g_avg_livestatus_usage.get(); }

double NebCore::averageLatencyGeneric() const {
    return g_average_active_latency;
}
double NebCore::averageLatencyRealTime() const { return 0.0; }
double NebCore::averageLatencyFetcher() const { return 0.0; }
double NebCore::averageLatencyChecker() const { return 0.0; }

double NebCore::helperUsageGeneric() const { return 0.0; }
double NebCore::helperUsageRealTime() const { return 0.0; }
double NebCore::helperUsageFetcher() const { return 0.0; }
double NebCore::helperUsageChecker() const { return 0.0; }

bool NebCore::hasEventHandlers() const { return g_any_event_handler_enabled; }

double NebCore::averageRunnableJobsFetcher() const { return 0.0; }
double NebCore::averageRunnableJobsChecker() const { return 0.0; }

std::chrono::system_clock::time_point NebCore::stateFileCreatedTime() const {
    return state_file_created_;
}

Encoding NebCore::dataEncoding() const { return _data_encoding; }
size_t NebCore::maxResponseSize() const { return _limits._max_response_size; }
size_t NebCore::maxCachedMessages() const {
    return _limits._max_cached_messages;
}

Logger *NebCore::loggerCore() const { return _logger; }
Logger *NebCore::loggerLivestatus() const { return _logger; }
Logger *NebCore::loggerRRD() const { return _logger; }

Triggers &NebCore::triggers() { return _triggers; }
const Triggers &NebCore::triggers() const { return _triggers; }

size_t NebCore::numQueuedNotifications() const { return 0; }
size_t NebCore::numQueuedAlerts() const { return 0; }

size_t NebCore::numCachedLogMessages() {
    return _store.numCachedLogMessages(*this);
}

namespace {
int pnpgraph_present(const std::filesystem::path &pnp_path,
                     const std::string &host, const std::string &service) {
    if (pnp_path.empty()) {
        return -1;
    }
    const std::filesystem::path path =
        pnp_path / pnp_cleanup(host) / (pnp_cleanup(service) + ".xml");
    std::error_code ec;
    (void)std::filesystem::status(path, ec);
    return ec ? 0 : 1;
}
}  // namespace

bool NebCore::isPnpGraphPresent(const IHost &h) const {
    return pnpgraph_present(paths()->rrd_multiple_directory(), h.name(),
                            dummy_service_description()) != 0;
}

bool NebCore::isPnpGraphPresent(const IService &s) const {
    return pnpgraph_present(paths()->rrd_multiple_directory(), s.host().name(),
                            s.description()) != 0;
}

namespace {
std::vector<std::string> toMetrics(const std::string &host_name,
                                   const std::string &description,
                                   const IPaths &paths, Logger *logger) {
    if (host_name.empty() || description.empty()) {
        return {};
    }
    std::vector<std::string> metrics;
    auto names = scan_rrd(paths.rrd_multiple_directory() / host_name,
                          description, logger);
    std::ranges::transform(names, std::back_inserter(metrics),
                           [](auto &&m) { return m.string(); });
    return metrics;
}
}  // namespace

std::vector<std::string> NebCore::metrics(const IHost &h) const {
    return toMetrics(h.name(), dummy_service_description(), *paths(), _logger);
}

std::vector<std::string> NebCore::metrics(const IService &s) const {
    return toMetrics(s.host_name(), s.description(), *paths(), _logger);
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
        // NOLINTNEXTLINE(bugprone-narrowing-conversions,cppcoreguidelines-narrowing-conversions)
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

MetricLocation NebCore::metricLocation(const std::string &host_name,
                                       const std::string &service_description,
                                       const Metric::Name &var) const {
    return MetricLocation{
        .path_ = paths()->rrd_multiple_directory() / host_name /
                 pnp_cleanup(service_description + "_" +
                             Metric::MangledName(var).string() + ".rrd"),
        .data_source_name_ = "1"};
}

bool NebCore::pnp4nagiosEnabled() const {
    return true;  // TODO(sp) ???
}

bool NebCore::isShuttingDown() const { return false; }

void NebCore::logRequest(const std::string &line,
                         const std::vector<std::string> &lines) {
    Informational log(_logger);
    log << "request: " << line;
    if (_logger->isLoggable(LogLevel::debug)) {
        for (const auto &l : lines) {
            log << R"(\n)" << l;
        }
    } else {
        const size_t s = lines.size();
        if (s > 0) {
            log << R"(\n{)" << s << (s == 1 ? " line follows" : " lines follow")
                << "...}";
        }
    }
}

bool NebCore::answerRequest(InputBuffer &input, OutputBuffer &output) {
    // Precondition: output has been reset
    const InputBuffer::Result res = input.readRequest();
    if (res != InputBuffer::Result::request_read) {
        if (res != InputBuffer::Result::eof) {
            std::ostringstream os;
            os << "terminating client connection: " << res;
            output.setError(OutputBuffer::ResponseCode::incomplete_request,
                            os.str());
        }
        return false;
    }
    const std::string line = input.nextLine();
    if (line.starts_with("GET ")) {
        return handleGet(input, output, line, mk::lstrip(line.substr(4)));
    }
    if (line.starts_with("GET")) {
        return handleGet(input, output, line, "");  // only to get error message
    }
    if (line.starts_with("COMMAND ")) {
        logRequest(line, {});
        try {
            answerCommandRequest(ExternalCommand(mk::lstrip(line.substr(8))));
        } catch (const std::invalid_argument &err) {
            Warning(_logger) << err.what();
        }
        return true;
    }
    logRequest(line, {});
    Warning(_logger) << "terminating client connection: invalid request '"
                     << line << "'";
    output.setError(OutputBuffer::ResponseCode::invalid_request,
                    "terminating client connection: invalid request method");
    return false;
}

bool NebCore::handleGet(InputBuffer &input, OutputBuffer &output,
                        const std::string &line,
                        const std::string &table_name) {
    auto lines = input.getLines();
    logRequest(line, lines);
    return _store.answerGetRequest(*this, lines, output, table_name);
}

void NebCore::answerCommandRequest(const ExternalCommand &command) {
    const auto name{command.name()};
    if (name == "MK_LOGWATCH_ACKNOWLEDGE") {
        answerCommandMkLogwatchAcknowledge(command);
        return;
    }
    if (name == "DEL_CRASH_REPORT") {
        answerCommandDelCrashReport(command);
        return;
    }
    if (name.starts_with("EC_")) {
        answerCommandEventConsole("COMMAND " + name.substr(3) +
                                  command.arguments());
        return;
    }
    // Nagios doesn't have a LOG or ROTATE_LOGFILE command, so we map it to a
    // custom command which we handle in broker_external_command().
    answerCommandNagios(name == "LOG" || name == "ROTATE_LOGFILE"
                            ? command.withName("_" + name)
                            : command);
}

void NebCore::answerCommandMkLogwatchAcknowledge(
    const ExternalCommand &command) {
    // COMMAND [1462191638] MK_LOGWATCH_ACKNOWLEDGE;host123;\var\log\syslog
    auto args = command.args();
    if (args.size() != 2) {
        Warning(_logger) << "MK_LOGWATCH_ACKNOWLEDGE expects 2 arguments";
        return;
    }
    mk_logwatch_acknowledge(_logger, _paths.logwatch_directory, args[0],
                            args[1]);
}

void NebCore::answerCommandDelCrashReport(const ExternalCommand &command) {
    auto args = command.args();
    if (args.size() != 1) {
        Warning(_logger) << "DEL_CRASH_REPORT expects 1 argument";
        return;
    }
    mk::crash_report::delete_id(_paths.crash_reports_directory, args[0],
                                _logger);
}

namespace {
class ECTableConnection : public EventConsoleConnection {
public:
    ECTableConnection(Logger *logger, std::string path, std::string command)
        : EventConsoleConnection(logger, std::move(path))
        , command_(std::move(command)) {}

private:
    void sendRequest(std::ostream &os) override { os << command_; }
    void receiveReply(std::istream & /*is*/) override {}
    std::string command_;
};
}  // namespace

void NebCore::answerCommandEventConsole(const std::string &command) {
    if (!mkeventdEnabled()) {
        Notice(_logger) << "event console disabled, ignoring command '"
                        << command << "'";
        return;
    }
    try {
        ECTableConnection(loggerLivestatus(),
                          _paths.event_console_status_socket, command)
            .run();
    } catch (const std::runtime_error &err) {
        Alert(_logger) << err.what();
    }
}

void NebCore::answerCommandNagios(const ExternalCommand &command) {
    const std::lock_guard<std::mutex> lg(_command_mutex);
    nagios_compat_submit_external_command(command.str().c_str());
}
