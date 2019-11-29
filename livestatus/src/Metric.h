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
#include <string>
#include <system_error>
#include <utility>
#include <vector>
#include "pnp4nagios.h"

class Logger;

class Metric {
public:
    class Name {
    public:
        explicit Name(std::string value) : _value(std::move(value)) {}
        [[nodiscard]] std::string string() const { return _value; }

    private:
        std::string _value;
    };

    class MangledName {
    public:
        explicit MangledName(const std::string &name)
            : _value(pnp_cleanup(name)) {}
        explicit MangledName(const Name &name) : MangledName(name.string()) {}
        [[nodiscard]] std::string string() const { return _value; }

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

/// Scan rrd in `basedir` and fill `Metric::Names` with metrics matching `desc`.
void scan_rrd(const std::filesystem::path &basedir, const std::string &desc,
              Metric::Names &, Logger *);

#endif  // Metric_h
