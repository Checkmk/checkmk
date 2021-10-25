// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDColumn_h
#define RRDColumn_h

#include "config.h"  // IWYU pragma: keep

// We keep <algorithm> for std::transform but IWYU wants it gone.
#include <algorithm>  // IWYU pragma: keep
#include <chrono>
#include <string>
#include <utility>
#include <variant>
#include <vector>
#ifndef CMC
#include "nagios.h"
#include "pnp4nagios.h"
#else
#include "Host.h"
#include "Object.h"
#endif

#include "ListColumn.h"
#include "overload.h"  // IWYU pragma: keep
class ListRenderer;
class MonitoringCore;

struct RRDColumnArgs {
    RRDColumnArgs(const std::string &arguments, const std::string &column_name);
    std::string rpn;
    long int start_time;
    long int end_time;
    int resolution;
    int max_entries;
};

namespace detail {
struct Data {
    using time_point = std::chrono::system_clock::time_point;
    Data() : step{0} {}
    Data(time_point s, time_point e, unsigned long d, std::vector<double> v)
        : start{s}, end{e}, step{d}, values{std::move(v)} {}
    time_point start;
    time_point end;
    unsigned long step;
    std::vector<double> values;

    [[nodiscard]] auto size() const { return values.size() + 3; }
    [[nodiscard]] auto cbegin() const { return values.begin(); }
    [[nodiscard]] auto cend() const { return values.end(); }
};
}  // namespace detail

class RRDDataMaker {
    using C = std::chrono::system_clock;

public:
    using value_type = std::variant<C::time_point, unsigned long, double>;
    RRDDataMaker(MonitoringCore *mc, RRDColumnArgs args)
        : _mc{mc}, _args{std::move(args)} {}

    template <class T>
    [[nodiscard]] std::vector<value_type> operator()(
        const T &row, std::chrono::seconds timezone_offset) const {
        const auto data = make(getHostNameServiceDesc(row));

        // We output meta data as first elements in the list. Note: In Python or
        // JSON we could output nested lists. In CSV mode this is not possible
        // and we rather stay compatible with CSV mode.
        std::vector<value_type> v;
        v.reserve(data.size());
        v.emplace_back(data.start + timezone_offset);
        v.emplace_back(data.end + timezone_offset);
        v.emplace_back(data.step);
        v.insert(v.end(), data.cbegin(), data.cend());

        return v;
    }

private:
    MonitoringCore *_mc;
    const RRDColumnArgs _args;

#ifndef CMC
    static std::pair<std::string, std::string> getHostNameServiceDesc(
        const host &row) {
        return {row.name, dummy_service_description()};
    }

    static std::pair<std::string, std::string> getHostNameServiceDesc(
        const service &row) {
        return {row.host_name, row.description};
    }
#else
    static std::pair<std::string, std::string> getHostNameServiceDesc(
        const Object &row) {
        return {row.host()->name(), row.serviceDescription()};
    }
#endif

    [[nodiscard]] detail::Data make(
        const std::pair<std::string, std::string>
            & /*host_name_service_description*/) const;
};

struct RRDRenderer : ListColumnRenderer<RRDDataMaker::value_type> {
    void output(ListRenderer &l, const value_type &value) const override {
        std::visit([&l](auto &&x) { l.output(x); }, value);
    }
};

namespace column::detail {
template <>
inline std::string serialize(const RRDDataMaker::value_type &v) {
    using C = std::chrono::system_clock;
    return std::visit(mk::overload{[](C::time_point x) {
                                       return std::to_string(C::to_time_t(x));
                                   },
                                   [](auto &&x) { return std::to_string(x); }},
                      v);
}
}  // namespace column::detail

#endif  // RRDColumn_h
