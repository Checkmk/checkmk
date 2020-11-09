// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NagiosCore.h"

#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <memory>
#include <ostream>
#include <utility>

#include "DowntimeOrComment.h"
#include "DowntimesOrComments.h"
#include "Logger.h"
#include "StringUtils.h"
#include "contact_fwd.h"
#include "pnp4nagios.h"

void NagiosPaths::dump(Logger *logger) const {
    Notice(logger) << "socket path = '" << _socket << "'";
    Notice(logger) << "pnp path = '" << _pnp << "'";
    Notice(logger) << "inventory path = '" << _mk_inventory << "'";
    Notice(logger) << "structured status path = '" << _structured_status << "'";
    Notice(logger) << "logwatch path = '" << _mk_logwatch << "'";
    Notice(logger) << "log file path = '" << _logfile << "'";
    Notice(logger) << "mkeventd socket path = '" << _mkeventd_socket << "'";
    Notice(logger) << "rrdcached socket path = '" << _rrdcached_socket << "'";
}

NagiosCore::NagiosCore(NagiosPaths paths, const NagiosLimits &limits,
                       NagiosAuthorization authorization,
                       Encoding data_encoding)
    : _logger_livestatus(Logger::getLogger("cmk.livestatus"))
    , _paths(std::move(paths))
    , _limits(limits)
    , _authorization(authorization)
    , _data_encoding(data_encoding)
    , _store(this) {
    extern host *host_list;
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

NagiosCore::Host *NagiosCore::getHostByDesignation(
    const std::string &designation) {
    auto it = _hosts_by_designation.find(mk::unsafe_tolower(designation));
    return it == _hosts_by_designation.end() ? nullptr : fromImpl(it->second);
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

bool NagiosCore::host_has_contact(const Host *host, const Contact *contact) {
    return is_authorized_for(this, toImpl(contact), toImpl(host), nullptr);
}

bool NagiosCore::is_contact_member_of_contactgroup(const ContactGroup *group,
                                                   const Contact *contact) {
    // Older Nagios headers are not const-correct... :-P
    return ::is_contact_member_of_contactgroup(
               const_cast<contactgroup *>(toImpl(group)),
               const_cast<::contact *>(toImpl(contact))) != 0;
}

std::chrono::system_clock::time_point NagiosCore::last_logfile_rotation() {
    // TODO(sp) We should better listen to NEBCALLBACK_PROGRAM_STATUS_DATA
    // instead of this 'extern' hack...
    extern time_t last_log_rotation;
    return std::chrono::system_clock::from_time_t(last_log_rotation);
}

std::chrono::system_clock::time_point NagiosCore::last_config_change() {
    // NOTE: Nagios doesn't reload, it restarts for config changes.
    extern time_t program_start;
    return std::chrono::system_clock::from_time_t(program_start);
}

size_t NagiosCore::maxLinesPerLogFile() const {
    return _limits._max_lines_per_logfile;
}

Command NagiosCore::find_command(const std::string &name) const {
    // Older Nagios headers are not const-correct... :-P
    if (command *cmd = ::find_command(const_cast<char *>(name.c_str()))) {
        return {cmd->name, cmd->command_line};
    }
    return {"", ""};
}

std::vector<Command> NagiosCore::commands() const {
    extern command *command_list;
    std::vector<Command> commands;
    for (command *cmd = command_list; cmd != nullptr; cmd = cmd->next) {
        commands.push_back({cmd->name, cmd->command_line});
    }
    return commands;
}

std::vector<DowntimeData> NagiosCore::downtimes_for_host(
    const Host *host) const {
    return downtimes_for_object(toImpl(host), nullptr);
}

std::vector<DowntimeData> NagiosCore::downtimes_for_service(
    const Service *service) const {
    return downtimes_for_object(toImpl(service)->host_ptr, toImpl(service));
}

std::vector<CommentData> NagiosCore::comments_for_host(const Host *host) const {
    return comments_for_object(toImpl(host), nullptr);
}

std::vector<CommentData> NagiosCore::comments_for_service(
    const Service *service) const {
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

std::filesystem::path NagiosCore::crashReportPath() const {
    return _paths._crash_reports_path;
}

std::filesystem::path NagiosCore::licenseUsageHistoryPath() const {
    return _paths._license_usage_history_path;
}

std::filesystem::path NagiosCore::pnpPath() const { return _paths._pnp; }

std::filesystem::path NagiosCore::historyFilePath() const {
    extern char *log_file;
    return log_file;
}

std::filesystem::path NagiosCore::logArchivePath() const {
    extern char *log_archive_path;
    return log_archive_path;
}

std::filesystem::path NagiosCore::rrdcachedSocketPath() const {
    return _paths._rrdcached_socket;
}

Encoding NagiosCore::dataEncoding() { return _data_encoding; }
size_t NagiosCore::maxResponseSize() { return _limits._max_response_size; }
size_t NagiosCore::maxCachedMessages() { return _limits._max_cached_messages; }

AuthorizationKind NagiosCore::serviceAuthorization() const {
    return _authorization._service;
}

AuthorizationKind NagiosCore::groupAuthorization() const {
    return _authorization._group;
}

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

void NagiosCore::registerDowntime(nebstruct_downtime_data *data) {
    _store.registerDowntime(data);
}

void NagiosCore::registerComment(nebstruct_comment_data *data) {
    _store.registerComment(data);
}

std::vector<DowntimeData> NagiosCore::downtimes_for_object(
    const ::host *h, const ::service *s) const {
    std::vector<DowntimeData> result;
    for (const auto &entry : _store._downtimes) {
        auto *dt = static_cast<Downtime *>(entry.second.get());
        if (dt->_host == h && dt->_service == s) {
            result.push_back({
                dt->_id,
                dt->_author_name,
                dt->_comment,
                false,
                std::chrono::system_clock::from_time_t(dt->_entry_time),
                std::chrono::system_clock::from_time_t(dt->_start_time),
                std::chrono::system_clock::from_time_t(dt->_end_time),
                dt->_fixed != 0,
                std::chrono::seconds(dt->_duration),
                0,
                dt->_type != 0,
            });
        }
    }
    return result;
}

std::vector<CommentData> NagiosCore::comments_for_object(
    const ::host *h, const ::service *s) const {
    std::vector<CommentData> result;
    for (const auto &entry : _store._comments) {
        auto *co = static_cast<Comment *>(entry.second.get());
        if (co->_host == h && co->_service == s) {
            result.push_back(
                {co->_id, co->_author_name, co->_comment,
                 static_cast<uint32_t>(co->_entry_type),
                 std::chrono::system_clock::from_time_t(co->_entry_time)});
        }
    }
    return result;
}
