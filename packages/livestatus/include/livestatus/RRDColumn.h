// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDColumn_h
#define RRDColumn_h

#include <chrono>
#include <string>
#include <utility>
#include <variant>
#include <vector>

#include "livestatus/ListColumn.h"
#include "livestatus/overload.h"  // IWYU pragma: keep

class IHost;
class IService;
class ListRenderer;
class ICore;

struct RRDColumnArgs {
    RRDColumnArgs(const std::string &arguments, const std::string &column_name);
    std::string rpn;
    long int start_time;
    long int end_time;
    int resolution;
    int max_entries;
};

class RRDDataMaker {
public:
    using C = std::chrono::system_clock;
    using value_type = std::variant<C::time_point, unsigned long, double>;

    RRDDataMaker(ICore *mc, RRDColumnArgs args)
        : _mc{mc}, _args{std::move(args)} {}

    std::vector<value_type> operator()(
        const IHost &hst, std::chrono::seconds timezone_offset) const;
    std::vector<value_type> operator()(
        const IService &svc, std::chrono::seconds timezone_offset) const;

private:
    ICore *_mc;
    const RRDColumnArgs _args;

    [[nodiscard]] std::vector<value_type> make(
        const std::string &host_name, const std::string &service_description,
        std::chrono::seconds timezone_offset) const;
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
