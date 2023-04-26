// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostListState_h
#define HostListState_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>

class IHost;
class IHostGroup;
class User;

#ifdef CMC
#include "CmcHostGroup.h"
class Host;
template <typename T>
class ObjectGroup;
#else
#include "NebHostGroup.h"
#include "nagios.h"
#endif

class HostListState {
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

    explicit HostListState(Type type) : type_(type) {}

    int32_t operator()(const IHostGroup &group, const User &user) const;

// TODO(sp): Remove.
#ifdef CMC
    int32_t operator()(const ObjectGroup<Host> &group, const User &user) const {
        return (*this)(CmcHostGroup{group}, user);
    }
#else
    int32_t operator()(const hostgroup &group, const User &user) const {
        return (*this)(NebHostGroup{group}, user);
    }
#endif

private:
    const Type type_;

    void update(const IHost &hst, const User &user, int32_t &result) const;
};

#endif  // HostListState_h
