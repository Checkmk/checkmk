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
#include <vector>

#include "DynamicRRDColumn.h"
#include "ListLambdaColumn.h"
#include "Renderer.h"
#include "Row.h"
#if defined(CMC)
#include "contact_fwd.h"
#else
#include "nagios.h"
#endif
class MonitoringCore;
class ColumnOffsets;

namespace detail {
class RRDDataMaker {
public:
    struct Data {
        std::chrono::system_clock::time_point start;
        std::chrono::system_clock::time_point end;
        unsigned long step{};
        std::vector<double> values;
    };
    RRDDataMaker(MonitoringCore *mc, RRDColumnArgs args)
        : _mc{mc}, _args{std::move(args)} {}

    template <class T>
    [[nodiscard]] Data operator()(const T &row) const {
        return make(getHostNameServiceDesc(row));
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

    static std::vector<std::string> defaultValue(
        std::chrono::seconds timezone_offset) {
        constexpr auto str = [](auto &&t) {
            return std::to_string(std::chrono::system_clock::to_time_t(
                std::chrono::system_clock::time_point{} + t));
        };
        return {str(timezone_offset), str(timezone_offset), std::to_string(0)};
    }
};

template <class T>
void RRDColumn<T>::output(Row row, RowRenderer &r,
                          const contact * /* auth_user */,
                          std::chrono::seconds /*timezone_offset*/) const {
    // We output meta data as first elements in the list. Note: In Python or
    // JSON we could output nested lists. In CSV mode this is not possible and
    // we rather stay compatible with CSV mode.
    const auto data = columnData<T>(row) == nullptr
                          ? detail::RRDDataMaker::Data{}
                          : data_maker_(*columnData<T>(row));
    ListRenderer l(r);
    l.output(data.start);
    l.output(data.end);
    l.output(data.step);
    for (const auto &value : data.values) {
        l.output(value);
    }
}

template <class T>
std::vector<std::string> RRDColumn<T>::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds timezone_offset) const {
    if (columnData<T>(row) == nullptr) {
        return defaultValue(timezone_offset);
    }
    const auto data = data_maker_(*columnData<T>(row));
    std::vector<std::string> strings;
    strings.push_back(std::to_string(
        std::chrono::system_clock::to_time_t(data.start + timezone_offset)));
    strings.push_back(std::to_string(
        std::chrono::system_clock::to_time_t(data.end + timezone_offset)));
    strings.push_back(std::to_string(data.step));
    std::transform(data.values.begin(), data.values.end(),
                   std::back_inserter(strings),
                   [](const auto &value) { return std::to_string(value); });
    return strings;
}

#include "RRDColumn-impl.h"  // IWYU pragma: keep

#endif  // RRDColumn_h
