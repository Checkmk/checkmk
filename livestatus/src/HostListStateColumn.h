// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostListStateColumn_h
#define HostListStateColumn_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>

#include "LogEntry.h"
#include "ServiceListStateColumn.h"
class MonitoringCore;

#ifdef CMC
#include <unordered_set>

#include "Host.h"
#include "Object.h"
#include "ObjectGroup.h"
#include "contact_fwd.h"
#else
#include "nagios.h"
#endif

class HostListStateColumn {
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

    HostListStateColumn(MonitoringCore *mc, Type logictype)
        : _mc(mc), _logictype(logictype) {}
#ifdef CMC
    int32_t operator()(const ObjectGroup &g, const contact *auth_user) const {
        auto v = value_type(g._objects.size());
        for (const auto &e : g._objects) {
            v.emplace(dynamic_cast<value_type::value_type>(e));
        }
        return (*this)(v, auth_user);
    }
#else
    int32_t operator()(const hostgroup &g, const contact *auth_user) const {
        return g.members == nullptr ? 0 : (*this)(g.members, auth_user);
    }
#endif
    int32_t operator()(const value_type &hsts, const contact *auth_user) const;

private:
    MonitoringCore *_mc;
    const Type _logictype;

    void update(const contact *auth_user, HostState current_state,
                bool has_been_checked,
                const ServiceListStateColumn::value_type &services,
                bool handled, int32_t &result) const;
};

#endif  // HostListStateColumn_h
