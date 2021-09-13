// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceListState_h
#define ServiceListState_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>
#include <functional>
#include <utility>

#include "LogEntry.h"
#include "auth.h"

#ifdef CMC
#include <memory>
#include <unordered_set>

#include "Host.h"
#include "ObjectGroup.h"
#include "contact_fwd.h"
class Service;
#else
#include "nagios.h"
#endif

class ServiceListState {
    // TODO(sp) Actually we want an input_range of services.
#ifdef CMC
    using value_type = std::unordered_set<const Service *>;
#else
    using value_type = servicesmember *;
#endif
    friend class HostListState;

public:
    enum class Type {
        num,
        num_pending,
        num_handled_problems,
        num_unhandled_problems,
        //
        num_ok,
        num_warn,
        num_crit,
        num_unknown,
        worst_state,
        //
        num_hard_ok,
        num_hard_warn,
        num_hard_crit,
        num_hard_unknown,
        worst_hard_state,
    };

    // NOTE: Due to an ugly technical reason, we have to delay getting the
    // service authorization, for details see the test
    // Store.TheCoreIsNotAccessedDuringConstructionOfTheStore.
    ServiceListState(std::function<ServiceAuthorization()> get_service_auth,
                     Type logictype)
        : _get_service_auth{std::move(get_service_auth)}
        , _logictype{logictype} {}

#ifdef CMC
    int32_t operator()(const Host &hst, const contact *auth_user) const {
        auto v = value_type(hst._services.size());
        for (const auto &e : hst._services) {
            v.emplace(e.get());
        }
        return (*this)(v, auth_user);
    }
    int32_t operator()(const ObjectGroup<Service> &g,
                       const contact *auth_user) const {
        return (*this)(value_type{g.begin(), g.end()}, auth_user);
    }
#else
    int32_t operator()(const host &hst, const contact *auth_user) const {
        return hst.services == nullptr ? 0 : (*this)(hst.services, auth_user);
    }
    int32_t operator()(const servicegroup &g, const contact *auth_user) const {
        return g.members == nullptr ? 0 : (*this)(g.members, auth_user);
    }
#endif
    int32_t operator()(const value_type &svcs, const contact *auth_user) const;

private:
    std::function<ServiceAuthorization()> _get_service_auth;
    const Type _logictype;
    static int32_t getValueFromServices(ServiceAuthorization service_auth,
                                        Type logictype, const value_type &svcs,
                                        const contact *auth_user);
    static void update(Type logictype, ServiceState current_state,
                       ServiceState last_hard_state, bool has_been_checked,
                       bool handled, int32_t &result);
};

#endif  // ServiceListState_h
