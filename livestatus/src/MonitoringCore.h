// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef MonitoringCore_h
#define MonitoringCore_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>
#include "StringUtils.h"
#include "Triggers.h"
#include "auth.h"
#include "data_encoding.h"
class Logger;

struct Command {
    std::string _name;
    std::string _command_line;
};

struct DowntimeData {
    unsigned long _id;
    std::string _author;
    std::string _comment;
    bool _origin_is_rule;
    std::chrono::system_clock::time_point _entry_time;
    std::chrono::system_clock::time_point _start_time;
    std::chrono::system_clock::time_point _end_time;
    bool _fixed;
    std::chrono::seconds _duration;
    int32_t _recurring;
    bool _pending;
};

struct CommentData {
    unsigned long _id;
    std::string _author;
    std::string _comment;
    uint32_t _entry_type;  // TODO(sp) Move Comment::Type here
    std::chrono::system_clock::time_point _entry_time;
};

using Attributes = std::unordered_map<std::string, std::string>;
enum class AttributeKind { custom_variables, tags, labels, label_sources };

inline std::tuple<AttributeKind, std::string> to_attribute_kind(
    const std::string &name) {
    if (mk::starts_with(name, "_TAG_")) {
        return {AttributeKind::tags, name.substr(5)};
    }
    if (mk::starts_with(name, "_LABEL_")) {
        return {AttributeKind::labels, name.substr(7)};
    }
    if (mk::starts_with(name, "_LABELSOURCE_")) {
        return {AttributeKind::label_sources, name.substr(13)};
    }
    return {AttributeKind::custom_variables, name};
}

/// An abstraction layer for the monitoring core (nagios or cmc)
class MonitoringCore {
public:
    class Contact;
    class ContactGroup;
    class Host;
    class Service;
    class TimePeriod;

    virtual ~MonitoringCore() = default;

    virtual Host *find_host(const std::string &name) = 0;
    virtual Host *getHostByDesignation(const std::string &designation) = 0;
    virtual Service *find_service(const std::string &host_name,
                                  const std::string &service_description) = 0;
    virtual ContactGroup *find_contactgroup(const std::string &name) = 0;

    virtual const Contact *find_contact(const std::string &name) = 0;
    virtual bool host_has_contact(const Host *host, const Contact *contact) = 0;
    virtual bool is_contact_member_of_contactgroup(const ContactGroup *group,
                                                   const Contact *contact) = 0;

    virtual std::chrono::system_clock::time_point last_logfile_rotation() = 0;
    virtual size_t maxLinesPerLogFile() const = 0;

    virtual Command find_command(const std::string &name) const = 0;
    virtual std::vector<Command> commands() const = 0;

    virtual std::vector<DowntimeData> downtimes_for_host(
        const Host *) const = 0;
    virtual std::vector<DowntimeData> downtimes_for_service(
        const Service *) const = 0;
    virtual std::vector<CommentData> comments_for_host(const Host *) const = 0;
    virtual std::vector<CommentData> comments_for_service(
        const Service *) const = 0;

    virtual bool mkeventdEnabled() = 0;

    virtual std::string mkeventdSocketPath() = 0;
    virtual std::string mkLogwatchPath() = 0;
    virtual std::string mkInventoryPath() = 0;
    virtual std::string structuredStatusPath() = 0;
    virtual std::string pnpPath() = 0;
    virtual std::string historyFilePath() = 0;
    virtual std::string logArchivePath() = 0;
    virtual std::string rrdcachedSocketPath() = 0;

    virtual Encoding dataEncoding() = 0;
    virtual size_t maxResponseSize() = 0;
    virtual size_t maxCachedMessages() = 0;

    virtual AuthorizationKind hostAuthorization() const = 0;
    virtual AuthorizationKind serviceAuthorization() const = 0;
    virtual AuthorizationKind groupAuthorization() const = 0;

    virtual Logger *loggerLivestatus() = 0;
    virtual Logger *loggerRRD() = 0;

    virtual Triggers &triggers() = 0;

    virtual size_t numQueuedNotifications() = 0;
    virtual size_t numQueuedAlerts() = 0;
    virtual size_t numCachedLogMessages() = 0;

    // TODO(sp) Horrible and fragile typing of the parameter, we need to fix
    // this: The type of the holder is either 'customvariablesmember *const *'
    // (NEB) or 'const Entity *' (CMC). Furthermore, all we need is a range for
    // iteration, not a copy. The kind parameter is not really OO, either...
    virtual Attributes customAttributes(const void *holder,
                                        AttributeKind kind) const = 0;

    // Our escape hatch, this should die in the long run...
    template <typename T>
    T *impl() const {
        return static_cast<T *>(implInternal());
    }

private:
    virtual void *implInternal() const = 0;
};

#endif  // MonitoringCore_h
