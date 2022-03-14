// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "MacroExpander.h"

#include <cstdlib>
#include <type_traits>
#include <unordered_map>
#include <utility>

#include "MonitoringCore.h"
#include "RegExp.h"
#include "StringUtils.h"
#include "nagios.h"

// static
std::optional<std::string> MacroExpander::from_ptr(const char *str) {
    return str == nullptr ? std::nullopt : std::make_optional(str);
}

std::string MacroExpander::expandMacros(const char *str) const {
    std::string raw{str == nullptr ? "" : str};
    std::string result;
    size_t pos = 0;
    while (pos < raw.size()) {
        auto start = raw.find('$', pos);
        if (start == std::string::npos) {
            result += raw.substr(pos);
            break;
        }
        auto end = raw.find('$', start + 1);
        if (end == std::string::npos) {
            result += raw.substr(pos);
            break;
        }
        auto macroname = raw.substr(start + 1, end - (start + 1));
        if (auto replacement = expand(macroname)) {
            result += raw.substr(pos, start - pos) + *replacement;
        } else {
            result += raw.substr(pos, end + 1 - pos);
        }
        pos = end + 1;
    }
    return result;
}

CompoundMacroExpander::CompoundMacroExpander(
    std::unique_ptr<MacroExpander> first, std::unique_ptr<MacroExpander> second)
    : _first(std::move(first)), _second(std::move(second)) {}

std::optional<std::string> CompoundMacroExpander::expand(
    const std::string &str) const {
    if (auto e = _first->expand(str)) {
        return e;
    }
    return _second->expand(str);
}

std::optional<std::string> UserMacroExpander::expand(
    const std::string &str) const {
    if (mk::starts_with(str, "USER")) {
        int n = atoi(str.substr(4).c_str());
        if (1 <= n && n <= MAX_USER_MACROS) {
            return from_ptr(macro_user[n - 1]);
        }
    }
    return {};
}

CustomVariableExpander::CustomVariableExpander(std::string prefix,
                                               const customvariablesmember *cvm,
                                               const MonitoringCore *mc)
    : _prefix(std::move(prefix)), _mc(mc), _cvm(cvm) {}

std::optional<std::string> CustomVariableExpander::expand(
    const std::string &str) const {
    if (!mk::starts_with(str, _prefix)) {
        return {};
    }

    RegExp re(str.substr(_prefix.size()), RegExp::Case::ignore,
              RegExp::Syntax::literal);
    for (const auto &[name, value] :
         _mc->customAttributes(&_cvm, AttributeKind::custom_variables)) {
        if (re.match(name)) {
            return value;
        }
    }
    return {};
}

HostMacroExpander::HostMacroExpander(const host *hst, const MonitoringCore *mc)
    : _hst(hst), _cve("_HOST", hst->custom_variables, mc) {}

// static
std::unique_ptr<MacroExpander> HostMacroExpander::make(const host &hst,
                                                       MonitoringCore *mc) {
    return std::make_unique<CompoundMacroExpander>(
        std::make_unique<HostMacroExpander>(&hst, mc),
        std::make_unique<UserMacroExpander>());
}

std::optional<std::string> HostMacroExpander::expand(
    const std::string &str) const {
    if (str == "HOSTNAME") {
        return from_ptr(_hst->name);
    }
    if (str == "HOSTDISPLAYNAME") {
        return from_ptr(_hst->display_name);
    }
    if (str == "HOSTALIAS") {
        return from_ptr(_hst->alias);
    }
    if (str == "HOSTADDRESS") {
        return from_ptr(_hst->address);
    }
    if (str == "HOSTOUTPUT") {
        return from_ptr(_hst->plugin_output);
    }
    if (str == "LONGHOSTOUTPUT") {
        return from_ptr(_hst->long_plugin_output);
    }
    if (str == "HOSTPERFDATA") {
        return from_ptr(_hst->perf_data);
    }
    if (str == "HOSTCHECKCOMMAND") {
        return from_ptr(nagios_compat_host_check_command(*_hst));
    }
    return _cve.expand(str);
}

ServiceMacroExpander::ServiceMacroExpander(const service *svc,
                                           const MonitoringCore *mc)
    : _svc(svc), _cve("_SERVICE", svc->custom_variables, mc) {}

// static
std::unique_ptr<MacroExpander> ServiceMacroExpander::make(const service &svc,
                                                          MonitoringCore *mc) {
    return std::make_unique<CompoundMacroExpander>(
        std::make_unique<HostMacroExpander>(svc.host_ptr, mc),
        std::make_unique<CompoundMacroExpander>(
            std::make_unique<ServiceMacroExpander>(&svc, mc),
            std::make_unique<UserMacroExpander>()));
}

std::optional<std::string> ServiceMacroExpander::expand(
    const std::string &str) const {
    if (str == "SERVICEDESC") {
        return from_ptr(_svc->description);
    }
    if (str == "SERVICEDISPLAYNAME") {
        return from_ptr(_svc->display_name);
    }
    if (str == "SERVICEOUTPUT") {
        return from_ptr(_svc->plugin_output);
    }
    if (str == "LONGSERVICEOUTPUT") {
        return from_ptr(_svc->long_plugin_output);
    }
    if (str == "SERVICEPERFDATA") {
        return from_ptr(_svc->perf_data);
    }
    if (str == "SERVICECHECKCOMMAND") {
        return from_ptr(nagios_compat_service_check_command(*_svc));
    }
    return _cve.expand(str);
}
