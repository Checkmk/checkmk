// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DowntimeColumn_h
#define DowntimeColumn_h

#include "config.h"  // IWYU pragma: keep

// We use `std::transform` but IWYU does not want the header.
#include <algorithm>  // IWYU pragma: keep
#include <chrono>
#include <iterator>
#include <string>
#include <vector>

#include "ListLambdaColumn.h"
#include "MonitoringCore.h"
#include "Row.h"
#ifdef CMC
#include "contact_fwd.h"
#else
#include "nagios.h"
#endif
class ColumnOffsets;
class RowRenderer;

#ifdef CMC
class Object;
#endif

class DowntimeColumn;

namespace detail {
class DowntimeRenderer {
public:
    enum class verbosity { none, medium, full };
    DowntimeRenderer(DowntimeColumn &c, verbosity v)
        : column_{c}, verbosity_{v} {}
    void operator()(Row row, RowRenderer &r) const;

private:
    DowntimeColumn &column_;
    verbosity verbosity_;
};
}  // namespace detail

class DowntimeColumn : public ListColumn {
public:
    using verbosity = detail::DowntimeRenderer::verbosity;
    template <class T>
    class Callback;
    DowntimeColumn(const std::string &name, const std::string &description,
                   const ColumnOffsets &offsets, verbosity v)
        : ListColumn{name, description, offsets}, renderer_{*this, v} {}

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

private:
    friend class detail::DowntimeRenderer;
    detail::DowntimeRenderer renderer_;
    [[nodiscard]] virtual std::vector<DowntimeData> getEntries(
        Row row) const = 0;
};

template <class T>
class DowntimeColumn::Callback : public DowntimeColumn {
public:
    Callback(const std::string &name, const std::string &description,
             const ColumnOffsets &offsets, DowntimeColumn::verbosity v,
             MonitoringCore *mc)
        : DowntimeColumn{name, description, offsets, v}, _mc{mc} {}

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    MonitoringCore *_mc;
    [[nodiscard]] std::vector<DowntimeData> getEntries(Row row) const override;
    [[nodiscard]] std::vector<DowntimeData> downtimes(const void *data) const;
};

/// \sa Apart from the lambda, the code is the same in
///    * CommentColumn::getValue()
///    * DowntimeColumn::getValue()
///    * ServiceGroupMembersColumn::getValue()
///    * ServiceListColumn::getValue()
template <class T>
std::vector<std::string> DowntimeColumn::Callback<T>::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    auto entries = getEntries(row);
    std::vector<std::string> values;
    std::transform(entries.begin(), entries.end(), std::back_inserter(values),
                   [](const auto &entry) { return std::to_string(entry._id); });
    return values;
}

template <class T>
std::vector<DowntimeData> DowntimeColumn::Callback<T>::getEntries(
    Row row) const {
    if (const auto *data = columnData<void>(row)) {
        return downtimes(data);
    }
    return {};
}

#ifdef CMC
template <>
inline std::vector<DowntimeData> DowntimeColumn::Callback<Object>::downtimes(
    const void *const data) const {
    return _mc->downtimes(reinterpret_cast<const MonitoringCore::Host *>(data));
}
#else
template <>
inline std::vector<DowntimeData> DowntimeColumn::Callback<host>::downtimes(
    const void *const data) const {
    return _mc->downtimes(reinterpret_cast<const MonitoringCore::Host *>(data));
}

template <>
inline std::vector<DowntimeData> DowntimeColumn::Callback<service>::downtimes(
    const void *const data) const {
    return _mc->downtimes(
        reinterpret_cast<const MonitoringCore::Service *>(data));
}
#endif
#endif  // DowntimeColumn_h
