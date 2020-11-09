// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef MacroExpander_h
#define MacroExpander_h

#include "config.h"  // IWYU pragma: keep

#include <memory>
#include <optional>
#include <string>

#include "nagios.h"
class MonitoringCore;

class MacroExpander {
public:
    virtual ~MacroExpander() = default;
    [[nodiscard]] virtual std::optional<std::string> expand(
        const std::string &str) const = 0;
    std::string expandMacros(const char *str) const;
    static std::optional<std::string> from_ptr(const char *str);
};

// poor man's monad...
class CompoundMacroExpander : public MacroExpander {
public:
    CompoundMacroExpander(std::unique_ptr<MacroExpander> first,
                          std::unique_ptr<MacroExpander> second);

    [[nodiscard]] std::optional<std::string> expand(
        const std::string &str) const override;

private:
    std::unique_ptr<MacroExpander> _first;
    std::unique_ptr<MacroExpander> _second;
};

class UserMacroExpander : public MacroExpander {
public:
    [[nodiscard]] std::optional<std::string> expand(
        const std::string &str) const override;
};

class CustomVariableExpander : public MacroExpander {
public:
    CustomVariableExpander(std::string prefix, const customvariablesmember *cvm,
                           const MonitoringCore *mc);

    [[nodiscard]] std::optional<std::string> expand(
        const std::string &str) const override;

private:
    std::string _prefix;
    const MonitoringCore *const _mc;
    const customvariablesmember *_cvm;
};

class HostMacroExpander : public MacroExpander {
public:
    HostMacroExpander(const host *hst, const MonitoringCore *mc);

    static std::unique_ptr<MacroExpander> make(const host &hst,
                                               MonitoringCore *mc);

    [[nodiscard]] std::optional<std::string> expand(
        const std::string &str) const override;

private:
    const host *_hst;
    CustomVariableExpander _cve;
};

class ServiceMacroExpander : public MacroExpander {
public:
    ServiceMacroExpander(const service *svc, const MonitoringCore *mc);

    static std::unique_ptr<MacroExpander> make(const service &svc,
                                               MonitoringCore *mc);

    [[nodiscard]] std::optional<std::string> expand(
        const std::string &str) const override;

private:
    const service *_svc;
    CustomVariableExpander _cve;
};
#endif  // MacroExpander_h
