// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Metric_h
#define Metric_h

#include <cstddef>
#include <filesystem>
#include <functional>
#include <string>
#include <utility>
#include <vector>

#include "livestatus/PnpUtils.h"

class Logger;

class Metric {
public:
    class Name {
    public:
        explicit Name(std::string value) : _value(std::move(value)) {}
        [[nodiscard]] std::string string() const { return _value; }

        auto operator<=>(const Name &) const = default;

    private:
        std::string _value;
    };

    class MangledName {
    public:
        explicit MangledName(const std::string &name)
            : _value(pnp_cleanup(name)) {}
        explicit MangledName(const Name &name) : MangledName(name.string()) {}
        [[nodiscard]] std::string string() const { return _value; }

        auto operator<=>(const MangledName &) const = default;

    private:
        std::string _value;
    };

    using Names = std::vector<MangledName>;

    Metric(std::string label, std::string value, std::string uom,
           std::string warn, std::string crit, std::string min, std::string max)
        : _name(std::move(label))
        , _mangled_name(_name)
        , _value(std::move(value))
        , _uom(std::move(uom))
        , _warn(std::move(warn))
        , _crit(std::move(crit))
        , _min(std::move(min))
        , _max(std::move(max)) {}

    [[nodiscard]] Name name() const { return _name; }
    [[nodiscard]] MangledName mangled_name() const { return _mangled_name; }
    [[nodiscard]] std::string value() const { return _value; }
    [[nodiscard]] double value_as_double() const;
    [[nodiscard]] std::string uom() const { return _uom; }
    [[nodiscard]] std::string warn() const { return _warn; }
    [[nodiscard]] std::string crit() const { return _crit; }
    [[nodiscard]] std::string min() const { return _min; }
    [[nodiscard]] std::string max() const { return _max; }

private:
    // We still need the original name for the Carbon interface, but apart from
    // that, we internally only use the mangled name, so we keep both.
    Name _name;
    MangledName _mangled_name;
    std::string _value;
    std::string _uom;
    std::string _warn;
    std::string _crit;
    std::string _min;
    std::string _max;
};

struct MetricLocation {
    std::filesystem::path path_;
    std::string data_source_name_;
};

namespace std {
template <>
struct hash<Metric::MangledName> {
    using argument_type = Metric::MangledName;
    using result_type = std::size_t;
    result_type operator()(argument_type const &n) const {
        return std::hash<std::string>{}(n.string());
    }
};
}  // namespace std

/// Scan rrd in `basedir` and return metrics matching `desc`.
Metric::Names scan_rrd(const std::filesystem::path &basedir,
                       const std::string &desc, Logger *);

#endif  // Metric_h
