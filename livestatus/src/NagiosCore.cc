// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NagiosCore.h"

#include <cstdlib>
#include <memory>
#include <sstream>
#include <utility>

#include "Logger.h"
#include "StringUtils.h"
#include "User.h"
#include "nagios.h"
#include "pnp4nagios.h"

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

NagiosCore::Host *NagiosCore::find_host(const std::string &name) {
    // Older Nagios headers are not const-correct... :-P
    return fromImpl(::find_host(const_cast<char *>(name.c_str())));
}

host *NagiosCore::getHostByDesignation(const std::string &designation) {
    auto it = _hosts_by_designation.find(mk::unsafe_tolower(designation));
    return it == _hosts_by_designation.end() ? nullptr : it->second;
}

NagiosCore::Service *NagiosCore::find_service(
    const std::string &host_name, const std::string &service_description) {
    // Older Nagios headers are not const-correct... :-P
    return fromImpl(
        ::find_service(const_cast<char *>(host_name.c_str()),
                       const_cast<char *>(service_description.c_str())));
}

NagiosCore::ContactGroup *NagiosCore::find_contactgroup(
    const std::string &name) {
    // Older Nagios headers are not const-correct... :-P
    return fromImpl(::find_contactgroup(const_cast<char *>(name.c_str())));
}

const NagiosCore::Contact *NagiosCore::find_contact(const std::string &name) {
    // Older Nagios headers are not const-correct... :-P
    return fromImpl(::find_contact(const_cast<char *>(name.c_str())));
}

std::unique_ptr<User> NagiosCore::find_user(const std::string &name) {
    // Older Nagios headers are not const-correct... :-P
    if (const auto *ctc = ::find_contact(const_cast<char *>(name.c_str()))) {
        return std::make_unique<AuthUser>(*ctc, _authorization._service,
                                          _authorization._group);
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

std::vector<DowntimeData> NagiosCore::downtimes(const Host *host) const {
    return downtimes_for_object(toImpl(host), nullptr);
}

std::vector<DowntimeData> NagiosCore::downtimes(const Service *service) const {
    return downtimes_for_object(toImpl(service)->host_ptr, toImpl(service));
}

std::vector<CommentData> NagiosCore::comments(const Host *host) const {
    return comments_for_object(toImpl(host), nullptr);
}

std::vector<CommentData> NagiosCore::comments(const Service *service) const {
    return comments_for_object(toImpl(service)->host_ptr, toImpl(service));
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

Logger *NagiosCore::loggerLivestatus() { return _logger_livestatus; }

Logger *NagiosCore::loggerRRD() { return loggerLivestatus(); }

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

Attributes NagiosCore::customAttributes(const void *holder,
                                        AttributeKind kind) const {
    const auto *h = *static_cast<const customvariablesmember *const *>(holder);
    Attributes attrs;
    for (const auto *cvm = h; cvm != nullptr; cvm = cvm->next) {
        auto [k, name] = to_attribute_kind(cvm->variable_name);
        if (k == kind) {
            switch (kind) {
                case AttributeKind::custom_variables:
                    attrs.emplace(name, cvm->variable_value);
                    break;
                case AttributeKind::tags:
                case AttributeKind::labels:
                case AttributeKind::label_sources:
                    attrs.emplace(b16decode(name),
                                  b16decode(cvm->variable_value));
                    break;
            }
        }
    }
    return attrs;
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

std::vector<DowntimeData> NagiosCore::downtimes_for_object(
    const ::host *h, const ::service *s) const {
    std::vector<DowntimeData> result;
    for (const auto &[id, dt] : _downtimes) {
        if (dt->_host == h && dt->_service == s) {
            result.push_back(DowntimeData{
                ._id = dt->_id,
                ._author = dt->_author,
                ._comment = dt->_comment,
                ._origin_is_rule = false,
                ._entry_time = dt->_entry_time,
                ._start_time = dt->_start_time,
                ._end_time = dt->_end_time,
                ._fixed = dt->_fixed,
                ._duration = dt->_duration,
                ._recurring = 0,
                ._pending = dt->_type != 0,
            });
        }
    }
    return result;
}

std::vector<CommentData> NagiosCore::comments_for_object(
    const ::host *h, const ::service *s) const {
    std::vector<CommentData> result;
    for (const auto &[id, co] : _comments) {
        if (co->_host == h && co->_service == s) {
            result.push_back(CommentData{._id = co->_id,
                                         ._author = co->_author,
                                         ._comment = co->_comment,
                                         ._entry_type = co->_entry_type,
                                         ._entry_time = co->_entry_time});
        }
    }
    return result;
}
