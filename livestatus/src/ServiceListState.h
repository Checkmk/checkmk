// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceListState_h
#define ServiceListState_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>

#include "LogEntry.h"
class User;

#ifdef CMC
#include <memory>
#include <unordered_set>

#include "Host.h"
#include "ObjectGroup.h"
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

    explicit ServiceListState(Type logictype) : _logictype{logictype} {}

#ifdef CMC
    int32_t operator()(const Host &hst, const User &user) const {
        auto v = value_type(hst._services.size());
        for (const auto &e : hst._services) {
            v.emplace(e.get());
        }
        return (*this)(v, user);
    }
    int32_t operator()(const ObjectGroup<Service> &g, const User &user) const {
        return (*this)(value_type{g.begin(), g.end()}, user);
    }
#else
    int32_t operator()(const host &hst, const User &user) const {
        return hst.services == nullptr ? 0 : (*this)(hst.services, user);
    }
    int32_t operator()(const servicegroup &g, const User &user) const {
        return g.members == nullptr ? 0 : (*this)(g.members, user);
    }
#endif
    int32_t operator()(const value_type &svcs, const User &user) const;

private:
    const Type _logictype;
    static int32_t getValueFromServices(const User &user, Type logictype,
                                        const value_type &svcs);
    static void update(Type logictype, ServiceState current_state,
                       ServiceState last_hard_state, bool has_been_checked,
                       bool handled, int32_t &result);
};

#endif  // ServiceListState_h
