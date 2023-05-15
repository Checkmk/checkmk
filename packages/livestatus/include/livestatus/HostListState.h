// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostListState_h
#define HostListState_h

#include <cstdint>

class IHost;
class IHostGroup;
class User;

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

private:
    const Type type_;

    void update(const IHost &hst, const User &user, int32_t &result) const;
};

#endif  // HostListState_h
