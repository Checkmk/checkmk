// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Provides simple, exception-free and always succeessful functions to access
// yaml data
// Returns either T
// on Fail empty otional or default

#pragma once
#include <string>
#include <string_view>

#include "common/yaml.h"
#include "logger.h"
namespace cma::yml {
void LogException(const std::string &format, std::string_view group,
                  std::string_view name, const std::exception &e);
void LogException(const std::string &format, std::string_view name,
                  const std::exception &e);
template <typename T>
std::optional<T> GetVal(YAML::Node yaml, const std::string &group_name,
                        const std::string &value_name) noexcept {
    if (yaml.size() == 0) return {};

    try {
        auto group = yaml[group_name];
        if (!group.IsMap()) {
            return {};
        }
        auto val = group[value_name];
        if (val.IsDefined() && !val.IsNull()) {
            return val.as<T>();
        }
        return {};
    } catch (const std::exception &e) {
        LogException("Cannot get yml value {} with {}.{} code:{}", group_name,
                     value_name, e);
    }

    return {};
}

template <typename T>
T GetVal(YAML::Node yaml, const std::string &group_name,
         const std::string &value_name, const T &dflt) noexcept {
    auto ret = GetVal<T>(yaml, group_name, value_name);
    if (ret) return *ret;

    return dflt;
}

inline YAML::Node GetNode(YAML::Node yaml, const std::string &section,
                          const std::string &name) noexcept {
    auto ret = GetVal<YAML::Node>(yaml, section, name);

    if (ret) return *ret;

    return {};
}

inline std::optional<YAML::Node> GetGroup(
    YAML::Node yaml, const std::string &value_name) noexcept {
    if (yaml.size() == 0) return {};

    try {
        auto node = yaml[value_name];
        return node;
    } catch (const std::exception &e) {
        LogException("Absent {} in YAML exception is '{}'", value_name, e);
    }
    return {};
}

// safe method yo extract value from the yaml
template <typename T>
std::optional<T> GetVal(YAML::Node yaml, const std::string &name) noexcept {
    if (yaml.size() == 0) return {};

    try {
        auto val = yaml[name];
        if (!val.IsDefined()) return {};

        if (val.IsScalar()) return val.as<T>();
        if (val.IsNull()) return {};
        return {};
    } catch (const std::exception &e) {
        LogException("Cannot read yml value '{}' code: [{}]", name, e);
    }

    return {};
}

template <>
inline std::optional<YAML::Node> GetVal(YAML::Node yaml,
                                        const std::string &name) noexcept {
    if (yaml.size() == 0) return {};

    try {
        return yaml[name];
    } catch (const std::exception &e) {
        LogException("Cannot read yml node '{}' code: [{}]", name, e);
    }

    return {};
}

template <typename T>
T GetVal(const YAML::Node &yaml, const std::string &name, T dflt) noexcept {
    auto ret = GetVal<T>(yaml, name);
    if (ret) return *ret;

    return dflt;
}

inline YAML::Node GetNode(const YAML::Node &yaml,
                          const std::string &name) noexcept {
    auto ret = GetVal<YAML::Node>(yaml, name);
    if (ret) return *ret;

    return {};
}

}  // namespace cma::yml
