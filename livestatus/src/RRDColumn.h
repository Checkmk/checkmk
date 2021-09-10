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
#include <iterator>
#include <string>
#include <utility>
#include <variant>
#include <vector>

#include "DynamicRRDColumn.h"
#include "ListLambdaColumn.h"
#include "Renderer.h"
#include "Row.h"
#include "overload.h"  // IWYU pragma: keep
#if defined(CMC)
#include "contact_fwd.h"
#else
#include "nagios.h"
#endif
class MonitoringCore;
class ColumnOffsets;

namespace detail {
struct Data {
    using time_point = std::chrono::system_clock::time_point;
    Data() : start{}, end{}, step{0}, values{} {}
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

    template <class T>
    [[nodiscard]] static std::pair<std::string, std::string>
    getHostNameServiceDesc(const T &row);

    [[nodiscard]] Data make(const std::pair<std::string, std::string>
                                & /*host_name_service_description*/) const;
};
}  // namespace detail

template <class T>
class RRDColumn : public ListColumn {
public:
    RRDColumn(const std::string &name, const std::string &description,
              const ColumnOffsets &offsets, MonitoringCore *mc,
              const RRDColumnArgs &args)
        : ListColumn{name, description, offsets}
        , data_maker_{detail::RRDDataMaker{mc, args}} {}

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    const detail::RRDDataMaker data_maker_;
    std::vector<detail::RRDDataMaker::value_type> getRawValue(
        Row row, std::chrono::seconds timezone_offset) const {
        return columnData<T>(row) == nullptr
                   ? std::vector<detail::RRDDataMaker::value_type>{}
                   : data_maker_(*columnData<T>(row), timezone_offset);
    }
};

template <class T>
void RRDColumn<T>::output(Row row, RowRenderer &r,
                          const contact * /* auth_user */,
                          std::chrono::seconds timezone_offset) const {
    const auto data = getRawValue(row, timezone_offset);
    ListRenderer l(r);
    for (const auto &value : data) {
        std::visit([&l](auto &&x) { l.output(x); }, value);
    }
}

template <class T>
std::vector<std::string> RRDColumn<T>::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds timezone_offset) const {
    const auto data = getRawValue(row, timezone_offset);

    using C = std::chrono::system_clock;
    std::vector<std::string> strings;
    std::transform(
        data.cbegin(), data.cend(), std::back_inserter(strings), [](auto &&e) {
            return std::visit(
                mk::overload{[](C::time_point x) {
                                 return std::to_string(C::to_time_t(x));
                             },
                             [](auto &&x) { return std::to_string(x); }},
                e);
        });
    return strings;
}

#include "RRDColumn-impl.h"  // IWYU pragma: keep

#endif  // RRDColumn_h
