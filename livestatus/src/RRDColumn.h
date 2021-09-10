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

#include "ListLambdaColumn.h"
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

class RRDDataMaker {
    using C = std::chrono::system_clock;

public:
    using value_type = std::variant<C::time_point, unsigned long, double>;
    RRDDataMaker(MonitoringCore *mc, RRDColumnArgs args)
        : _mc{mc}, _args{std::move(args)} {}

    template <class T>
    [[nodiscard]] std::vector<value_type> operator()(
        const T &row, std::chrono::seconds timezone_offset) const {
        return make(getHostNameServiceDesc(row), timezone_offset);
    }

private:
    MonitoringCore *_mc;
    const RRDColumnArgs _args;

    template <class T>
    [[nodiscard]] static std::pair<std::string, std::string>
    getHostNameServiceDesc(const T &row);

    [[nodiscard]] std::vector<value_type> make(
        const std::pair<std::string, std::string>
            & /*host_name_service_description*/,
        std::chrono::seconds /*timezone_offset*/) const;
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

#include "RRDColumn-impl.h"  // IWYU pragma: keep

#endif  // RRDColumn_h
