// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef auth_h
#define auth_h

#include "config.h"  // IWYU pragma: keep

#include <string>

#ifdef CMC
#include "contact_fwd.h"
class Host;  // IWYU pragma: keep
using host = Host;
class Service;  // IWYU pragma: keep
using service = Service;
// IWYU pragma: no_include "ObjectGroup.h"
template <typename T>
class ObjectGroup;  // IWYU pragma: keep
using hostgroup = ObjectGroup<Host>;
using servicegroup = ObjectGroup<Service>;
#else
#include "nagios.h"
#endif

enum class ServiceAuthorization {
    loose = 0,   // contacts for hosts see all services
    strict = 1,  // must be explicit contact of a service
};

enum class GroupAuthorization {
    loose = 0,   // sufficient to be contact for one member
    strict = 1,  // must be contact of all members

};

inline contact *no_auth_user() { return nullptr; }

inline contact *unknown_auth_user() {
    return reinterpret_cast<contact *>(0xdeadbeaf);
}

// NOTE: Although technically not necessary (C functions in Nagios vs. C++
// functions with mangled names), we avoid name clashes with the Nagios API
// here to avoid confusion.
bool is_authorized_for_hst(const contact *ctc, const host *hst);
bool is_authorized_for_svc(ServiceAuthorization service_auth,
                           const contact *ctc, const service *svc);
bool is_authorized_for_host_group(GroupAuthorization group_auth,
                                  const hostgroup *hg, const contact *ctc);
bool is_authorized_for_service_group(GroupAuthorization group_auth,
                                     ServiceAuthorization service_auth,
                                     const servicegroup *sg,
                                     const contact *ctc);

class User {
    const contact *auth_user_;
    ServiceAuthorization service_auth_;
    GroupAuthorization group_auth_;

public:
    User(const contact *auth_user, ServiceAuthorization service_auth,
         GroupAuthorization group_auth);

    [[nodiscard]] bool is_authorized_for_everything() const;
    [[nodiscard]] bool is_authorized_for_host(const host &hst) const;
    [[nodiscard]] bool is_authorized_for_service(const service &svc) const;
    [[nodiscard]] bool is_authorized_for_host_group(const hostgroup &hg) const;
    [[nodiscard]] bool is_authorized_for_service_group(
        const servicegroup &sg) const;
    [[nodiscard]] bool is_authorized_for_event(
        const std::string &precedence, const std::string &contact_groups,
        const host *hst) const;

    // TODO(sp) Nuke this!
    [[nodiscard]] const contact *authUser() const { return auth_user_; }
};

#endif  // auth_h
