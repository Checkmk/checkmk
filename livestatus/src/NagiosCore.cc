// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NagiosCore.h"

#include <cstdlib>
#include <sstream>
#include <utility>

#include "Comment.h"
#include "NebComment.h"
#include "NebContact.h"
#include "NebContactGroup.h"
#include "NebDowntime.h"
#include "NebHost.h"
#include "NebService.h"
#include "NebTimeperiod.h"
#include "livestatus/Interface.h"
#include "livestatus/Logger.h"
#include "livestatus/PnpUtils.h"
#include "livestatus/StringUtils.h"

void NagiosPaths::dump(Logger *logger) const {
    Notice(logger) << "socket path = '" << _socket << "'";
    Notice(logger) << "pnp path = '" << _pnp << "'";
    Notice(logger) << "inventory path = '" << _mk_inventory << "'";
    Notice(logger) << "structured status path = '" << _structured_status << "'";
    Notice(logger) << "robotmk html log path = '" << _robotmk_html_log_path
                   << "'";
    Notice(logger) << "logwatch path = '" << _mk_logwatch << "'";
    Notice(logger) << "log file path = '" << _logfile << "'";
    Notice(logger) << "mkeventd socket path = '" << _mkeventd_socket << "'";
    Notice(logger) << "rrdcached socket path = '" << _rrdcached_socket << "'";
}

NagiosCore::NagiosCore(
    std::map<unsigned long, std::unique_ptr<Downtime>> &downtimes,
    std::map<unsigned long, std::unique_ptr<Comment>> &comments,
    NagiosPaths paths, const NagiosLimits &limits,
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
    return ToIHost(::find_host(const_cast<char *>(name.c_str())));
}

std::unique_ptr<const IHost> NagiosCore::getHostByDesignation(
    const std::string &designation) {
    auto it = _hosts_by_designation.find(mk::unsafe_tolower(designation));
    auto *host = it == _hosts_by_designation.end() ? nullptr : it->second;
    return ToIHost(host);
}

std::unique_ptr<const IService> NagiosCore::find_service(
    const std::string &host_name, const std::string &service_description) {
    // Older Nagios headers are not const-correct... :-P
    return ToIService(
        ::find_service(const_cast<char *>(host_name.c_str()),
                       const_cast<char *>(service_description.c_str())));
}

std::unique_ptr<const IContactGroup> NagiosCore::find_contactgroup(
    const std::string &name) {
    return std::make_unique<NebContactGroup>(name);
}

std::unique_ptr<const IContact> NagiosCore::find_contact(
    const std::string &name) {
    // Older Nagios headers are not const-correct... :-P
    const auto *c = ::find_contact(const_cast<char *>(name.c_str()));
    return c == nullptr ? nullptr : std::make_unique<NebContact>(*c);
}

std::unique_ptr<User> NagiosCore::find_user(const std::string &name) {
    // Older Nagios headers are not const-correct... :-P
    if (const auto *ctc = ::find_contact(const_cast<char *>(name.c_str()))) {
        return std::make_unique<AuthUser>(
            NebContact{*ctc}, _authorization._service, _authorization._group,
            [](const std::string &name) {
                return std::make_unique<NebContactGroup>(name);
            });
    }
    return std::make_unique<UnknownUser>();
}

std::chrono::system_clock::time_point NagiosCore::last_logfile_rotation() {
    // TODO(sp) We should better listen to NEBCALLBACK_PROGRAM_STATUS_DATA
    // instead of this 'extern' hack...
    return std::chrono::system_clock::from_time_t(last_log_rotation);
}

std::chrono::system_clock::time_point NagiosCore::last_config_change() {
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

std::vector<std::unique_ptr<const IComment>> NagiosCore::comments(
    const IHost &hst) const {
    // TODO(sp): Do we need a mutex here?
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
    const IService &svc) const {
    // TODO(sp): Do we need a mutex here?
    std::vector<std::unique_ptr<const IComment>> result;
    for (const auto &[id, co] : _comments) {
        if (co->_host == static_cast<const service *>(svc.handle())->host_ptr &&
            co->_service == static_cast<const service *>(svc.handle())) {
            result.emplace_back(std::make_unique<NebComment>(*co));
        }
    }
    return result;
}

void NagiosCore::forEachCommentUntil(
    // TODO(sp): Do we need a mutex here?
    const std::function<bool(const IComment &)> &f) const {
    for (const auto &[id, co] : _comments) {
        if (f(NebComment{*co})) {
            break;
        }
    }
}

std::vector<std::unique_ptr<const IDowntime>> NagiosCore::downtimes(
    const IHost &hst) const {
    // TODO(sp): Do we need a mutex here?
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
    const IService &svc) const {
    // TODO(sp): Do we need a mutex here?
    std::vector<std::unique_ptr<const IDowntime>> result;
    for (const auto &[id, dt] : _downtimes) {
        if (dt->_host == static_cast<const service *>(svc.handle())->host_ptr &&
            dt->_service == static_cast<const service *>(svc.handle())) {
            result.emplace_back(std::make_unique<NebDowntime>(*dt));
        }
    }
    return result;
}

void NagiosCore::forEachDowntimeUntil(
    // TODO(sp): Do we need a mutex here?
    const std::function<bool(const IDowntime &)> &f) const {
    for (const auto &[id, dt] : _downtimes) {
        if (f(NebDowntime{*dt})) {
            break;
        }
    }
}

void NagiosCore::forEachLabelUntil(
    const std::function<bool(const std::string &name, const std::string &value)>
        & /*f*/) const {}

void NagiosCore::forEachTimeperiodUntil(
    const std::function<bool(const ITimeperiod &)> &f) const {
    for (const timeperiod *tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        if (f(NebTimeperiod{*tp})) {
            break;
        }
    }
}

bool NagiosCore::mkeventdEnabled() {
    if (const char *config_mkeventd = getenv("CONFIG_MKEVENTD")) {
        return config_mkeventd == std::string("on");
    }
    return false;
}

std::filesystem::path NagiosCore::mkeventdSocketPath() const {
    return _paths._mkeventd_socket;
}

std::filesystem::path NagiosCore::mkLogwatchPath() const {
    return _paths._mk_logwatch;
}

std::filesystem::path NagiosCore::mkInventoryPath() const {
    return _paths._mk_inventory;
}

std::filesystem::path NagiosCore::structuredStatusPath() const {
    return _paths._structured_status;
}

std::filesystem::path NagiosCore::robotMkHtmlLogPath() const {
    return _paths._robotmk_html_log_path;
}

std::filesystem::path NagiosCore::crashReportPath() const {
    return _paths._crash_reports_path;
}

std::filesystem::path NagiosCore::licenseUsageHistoryPath() const {
    return _paths._license_usage_history_path;
}

std::filesystem::path NagiosCore::pnpPath() const { return _paths._pnp; }

std::filesystem::path NagiosCore::historyFilePath() const { return log_file; }

std::filesystem::path NagiosCore::logArchivePath() const {
    return log_archive_path;
}

std::filesystem::path NagiosCore::rrdcachedSocketPath() const {
    return _paths._rrdcached_socket;
}

Encoding NagiosCore::dataEncoding() { return _data_encoding; }
size_t NagiosCore::maxResponseSize() { return _limits._max_response_size; }
size_t NagiosCore::maxCachedMessages() { return _limits._max_cached_messages; }

Logger *NagiosCore::loggerCore() { return _logger_livestatus; }
Logger *NagiosCore::loggerLivestatus() { return _logger_livestatus; }
Logger *NagiosCore::loggerRRD() { return _logger_livestatus; }

Triggers &NagiosCore::triggers() { return _triggers; }

size_t NagiosCore::numQueuedNotifications() { return 0; }
size_t NagiosCore::numQueuedAlerts() { return 0; }

size_t NagiosCore::numCachedLogMessages() {
    return _store.numCachedLogMessages();
}

namespace {
// Nagios converts custom attribute names to uppercase, splits name/value at
// space, uses ';' as a comment character, is line-oriented, etc. etc. So we use
// a base16 encoding for names and values of tags, labels, and label sources,
// e.g. "48656C6C6F2C20776F726C6421" => "Hello, world!".
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
        pnpPath() / host_name /
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
