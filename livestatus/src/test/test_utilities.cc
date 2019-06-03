// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "test_utilities.h"
#include <type_traits>
#include <utility>

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
    host_check_command = cc("the host check command");
    custom_variables = cust_vars_.start();
    plugin_output = cc("the plugin output");
    long_plugin_output = cc("the long plugin output");
    perf_data = cc("the perf data");
}

TestService::TestService(host *h, const Attributes &cust_vars)
    : cust_vars_(cust_vars) {
    description = cc("muppet_show");
    display_name = cc("The Muppet Show");
    service_check_command = cc("check_fozzie_bear");
    custom_variables = cust_vars_.start();
    plugin_output = cc("plug");
    long_plugin_output = cc("long plug");
    perf_data = cc("99%");
    host_ptr = h;
}
