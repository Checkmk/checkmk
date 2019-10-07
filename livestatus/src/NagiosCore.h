// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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

#ifndef NagiosCore_h
#define NagiosCore_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <cstddef>
#include <string>
#include <unordered_map>
#include <vector>
#include "MonitoringCore.h"
#include "Store.h"
#include "Triggers.h"
#include "auth.h"
#include "contact_fwd.h"
#include "data_encoding.h"
#include "nagios.h"
class InputBuffer;
class Logger;
class OutputBuffer;

struct NagiosPaths {
    std::string _socket{"/usr/local/nagios/var/rw/live"};
    std::string _pnp;
    std::string _mk_inventory;
    std::string _structured_status;
    std::string _mk_logwatch;
    std::string _logfile;
    std::string _mkeventd_socket;
    std::string _rrdcached_socket;

    void dump(Logger *logger);
};

struct NagiosLimits {
    size_t _max_cached_messages{500000};
    size_t _max_lines_per_logfile{1000000};
    size_t _max_response_size{100 * 1024 * 1024};
};

struct NagiosAuthorization {
    AuthorizationKind _service{AuthorizationKind::loose};
    AuthorizationKind _group{AuthorizationKind::strict};
};

class NagiosCore : public MonitoringCore {
public:
    NagiosCore(NagiosPaths paths, const NagiosLimits &limits,
               NagiosAuthorization authorization, Encoding data_encoding);

    Host *find_host(const std::string &name) override;
    Host *getHostByDesignation(const std::string &designation) override;
    Service *find_service(const std::string &host_name,
                          const std::string &service_description) override;
    ContactGroup *find_contactgroup(const std::string &name) override;

    const Contact *find_contact(const std::string &name) override;
    bool host_has_contact(const Host *host, const Contact *contact) override;
    bool is_contact_member_of_contactgroup(const ContactGroup *group,
                                           const Contact *contact) override;

    std::chrono::system_clock::time_point last_logfile_rotation() override;
    size_t maxLinesPerLogFile() const override;

    Command find_command(const std::string &name) const override;
    std::vector<Command> commands() const override;

    std::vector<DowntimeData> downtimes_for_host(
        const Host *host) const override;
    std::vector<DowntimeData> downtimes_for_service(
        const Service *service) const override;
    std::vector<CommentData> comments_for_host(const Host *host) const override;
    std::vector<CommentData> comments_for_service(
        const Service *service) const override;

    bool mkeventdEnabled() override;

    std::string mkeventdSocketPath() override;
    std::string mkLogwatchPath() override;
    std::string mkInventoryPath() override;
    std::string structuredStatusPath() override;
    std::string pnpPath() override;
    std::string historyFilePath() override;
    std::string logArchivePath() override;
    std::string rrdcachedSocketPath() override;

    Encoding dataEncoding() override;
    size_t maxResponseSize() override;
    size_t maxCachedMessages() override;

    AuthorizationKind serviceAuthorization() const override;
    AuthorizationKind groupAuthorization() const override;

    Logger *loggerLivestatus() override;
    Logger *loggerRRD() override;

    Triggers &triggers() override;

    size_t numQueuedNotifications() override;
    size_t numQueuedAlerts() override;
    size_t numCachedLogMessages() override;

    Attributes customAttributes(const void *holder,
                                AttributeKind kind) const override;

    // specific for NagiosCore
    bool answerRequest(InputBuffer &input, OutputBuffer &output);
    void registerDowntime(nebstruct_downtime_data *data);
    void registerComment(nebstruct_comment_data *data);

private:
    Logger *_logger_livestatus;
    const NagiosPaths _paths;
    const NagiosLimits _limits;
    const NagiosAuthorization _authorization;
    Encoding _data_encoding;
    Store _store;
    std::unordered_map<std::string, host *> _hosts_by_designation;
    Triggers _triggers;

    void *implInternal() const override { return const_cast<Store *>(&_store); }

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
