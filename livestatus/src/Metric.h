// .------------------------------------------------------------------------.
// |                ____ _               _        __  __ _  __              |
// |               / ___| |__   ___  ___| | __   |  \/  | |/ /              |
// |              | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /               |
// |              | |___| | | |  __/ (__|   <    | |  | | . \               |
// |               \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\              |
// |                                        |_____|                         |
// |             _____       _                       _                      |
// |            | ____|_ __ | |_ ___ _ __ _ __  _ __(_)___  ___             |
// |            |  _| | '_ \| __/ _ \ '__| '_ \| '__| / __|/ _ \            |
// |            | |___| | | | ||  __/ |  | |_) | |  | \__ \  __/            |
// |            |_____|_| |_|\__\___|_|  | .__/|_|  |_|___/\___|            |
// |                                     |_|                                |
// |                     _____    _ _ _   _                                 |
// |                    | ____|__| (_) |_(_) ___  _ __                      |
// |                    |  _| / _` | | __| |/ _ \| '_ \                     |
// |                    | |__| (_| | | |_| | (_) | | | |                    |
// |                    |_____\__,_|_|\__|_|\___/|_| |_|                    |
// |                                                                        |
// | mathias-kettner.com                                 mathias-kettner.de |
// '------------------------------------------------------------------------'
//  This file is part of the Check_MK Enterprise Edition (CEE).
//  Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
//  Distributed under the Check_MK Enterprise License.
//
//  You should have  received  a copy of the Check_MK Enterprise License
//  along with Check_MK. If not, email to mk@mathias-kettner.de
//  or write to the postal address provided at www.mathias-kettner.de

#ifndef Metric_h
#define Metric_h

#include "config.h"  // IWYU pragma: keep
#include <cstddef>
#include <filesystem>
#include <functional>
#include <string>
#include <utility>
#include "pnp4nagios.h"

class Metric {
public:
    class Name {
    public:
        explicit Name(std::string value) : _value(std::move(value)) {}
        std::string string() const { return _value; }

    private:
        std::string _value;
    };

    class MangledName {
    public:
        explicit MangledName(const Name &name)
            : _value(pnp_cleanup(name.string())) {}
        std::string string() const { return _value; }

    private:
        std::string _value;
    };

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

    Name name() const { return _name; }
    MangledName mangled_name() const { return _mangled_name; }
    std::string value() const { return _value; }
    std::string uom() const { return _uom; }
    std::string warn() const { return _warn; }
    std::string crit() const { return _crit; }
    std::string min() const { return _min; }
    std::string max() const { return _max; }

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

inline bool operator==(const Metric::MangledName &x,
                       const Metric::MangledName &y) {
    return x.string() == y.string();
}

inline bool operator!=(const Metric::MangledName &x,
                       const Metric::MangledName &y) {
    return !(x == y);
}

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

#endif  // Metric_h
