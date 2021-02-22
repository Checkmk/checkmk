// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceListState_h
#define ServiceListState_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>

#include "LogEntry.h"
class MonitoringCore;

#ifdef CMC
#include <memory>
#include <unordered_set>

#include "Host.h"
#include "Object.h"
#include "ObjectGroup.h"
#include "Service.h"
#include "cmc.h"
#else
#include "nagios.h"
#endif

class ServiceListState {
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

    ServiceListState(MonitoringCore *mc, Type logictype)
        : _mc(mc), _logictype(logictype) {}

#ifdef CMC
    int32_t operator()(const Host &hst, const contact *auth_user) const {
        auto v = value_type(hst._services.size());
        for (const auto &e : hst._services) {
            v.emplace(e.get());
        }
        return (*this)(v, auth_user);
    }
    int32_t operator()(const ObjectGroup &g, const contact *auth_user) const {
        auto v = value_type(g._objects.size());
        for (const auto &e : g._objects) {
            v.emplace(dynamic_cast<value_type::value_type>(e));
        }
        return (*this)(v, auth_user);
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
    MonitoringCore *_mc;
    const Type _logictype;
    static int32_t getValueFromServices(MonitoringCore *mc, Type logictype,
                                        const value_type &svcs,
                                        const contact *auth_user);
    static void update(Type logictype, ServiceState current_state,
                       ServiceState last_hard_state, bool has_been_checked,
                       bool handled, int32_t &result);
};

#endif  // ServiceListState_h
