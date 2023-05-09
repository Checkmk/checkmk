// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef auth_h
#define auth_h

#include "config.h"  // IWYU pragma: keep

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

#endif  // auth_h
