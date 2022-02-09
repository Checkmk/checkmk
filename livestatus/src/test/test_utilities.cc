// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "test_utilities.h"

#include <type_traits>
#include <unordered_map>
#include <utility>

#include "nagios.h"

char *cc(const char *str) { return const_cast<char *>(str); }

CustomVariables::CustomVariables(Attributes attrs) : attrs_(std::move(attrs)) {
    cvms_.reserve(attrs_.size());  // IMPORTANT: No reallocations later!
    customvariablesmember *last = nullptr;
    for (const auto &[name, value] : attrs_) {  // IMPORTANT: Use refs!
        cvms_.push_back({cc(name.c_str()), cc(value.c_str()), 0, last});
        last = &cvms_.back();
    }
}

customvariablesmember *CustomVariables::start() { return &cvms_.back(); }

TestHost::TestHost(const Attributes &cust_vars) : cust_vars_(cust_vars) {
    name = cc("sesame_street");
    display_name = cc("the display name");
    alias = cc("the alias");
    address = cc("the address");
    nagios_compat_host_check_command(*this) = cc("the host check command");
    custom_variables = cust_vars_.start();
    plugin_output = cc("the plugin output");
    long_plugin_output = cc("the long plugin output");
    perf_data = cc("the perf data");
}

TestService::TestService(host *h, const Attributes &cust_vars)
    : cust_vars_(cust_vars) {
    description = cc("muppet_show");
    display_name = cc("The Muppet Show");
    nagios_compat_service_check_command(*this) = cc("check_fozzie_bear");
    custom_variables = cust_vars_.start();
    plugin_output = cc("plug");
    long_plugin_output = cc("long plug");
    perf_data = cc("99%");
    host_ptr = h;
}
