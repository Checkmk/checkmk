// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostListState_h
#define HostListState_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>

#include "ServiceListState.h"
#include "livestatus/LogEntry.h"
class User;

#ifdef CMC
#include <unordered_set>

#include "ObjectGroup.h"
class Host;
#else
#include "nagios.h"
#endif

class HostListState {
    // TODO(sp) Actually we want an input_range of hosts.
#ifdef CMC
    using value_type = std::unordered_set<const Host *>;
#else
    using value_type = hostsmember *;
#endif

public:
    enum class Type {
        num_hst,
        num_hst_pending,
        num_hst_handled_problems,
        num_hst_unhandled_problems,
        //
        num_hst_up,
        num_hst_down,
        num_hst_unreach,
        worst_hst_state,
        //
        num_svc,
        num_svc_pending,
        num_svc_handled_problems,
        num_svc_unhandled_problems,
        //
        num_svc_ok,
        num_svc_warn,
        num_svc_crit,
        num_svc_unknown,
        worst_svc_state,
        //
        num_svc_hard_ok,
        num_svc_hard_warn,
        num_svc_hard_crit,
        num_svc_hard_unknown,
        worst_svc_hard_state,
    };

    // NOTE: Due to an ugly technical reason, we have to delay getting the
    // service authorization, for details see the test
    // Store.TheCoreIsNotAccessedDuringConstructionOfTheStore.
    explicit HostListState(Type logictype) : _logictype(logictype) {}
#ifdef CMC
    int32_t operator()(const ObjectGroup<Host> &g, const User &user) const {
        return (*this)(value_type{g.begin(), g.end()}, user);
    }
#else
    int32_t operator()(const hostgroup &g, const User &user) const {
        return g.members == nullptr ? 0 : (*this)(g.members, user);
    }
#endif
    int32_t operator()(const value_type &hsts, const User &user) const;

private:
    const Type _logictype;

    void update(const User &user, HostState current_state,
                bool has_been_checked,
                const ServiceListState::value_type &services, bool handled,
                int32_t &result) const;
};

#endif  // HostListState_h
