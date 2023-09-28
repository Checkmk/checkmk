// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceListState_h
#define ServiceListState_h

#include <cstdint>

class IHost;
class IService;
class IServiceGroup;
class User;

class ServiceListState {
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

    explicit ServiceListState(Type type) : type_{type} {}

    int32_t operator()(const IHost &hst, const User &user) const;
    int32_t operator()(const IServiceGroup &g, const User &user) const;

private:
    const Type type_;

    void update(const IService &svc, const User &user, int32_t &result) const;
};

#endif  // ServiceListState_h
