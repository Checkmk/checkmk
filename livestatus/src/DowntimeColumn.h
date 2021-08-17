// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DowntimeColumn_h
#define DowntimeColumn_h

#include "config.h"  // IWYU pragma: keep

// We use `std::transform` but IWYU does not want the header.
#include <algorithm>  // IWYU pragma: keep
#include <memory>
#include <string>
#include <utility>

#include "ListLambdaColumn.h"
#include "MonitoringCore.h"
#ifdef CMC
#include "contact_fwd.h"
#endif
class ColumnOffsets;
class ListRenderer;

class DowntimeRenderer : public ListColumnRenderer<DowntimeData> {
public:
    enum class verbosity { none, medium, full };
    DowntimeRenderer(verbosity v) : verbosity_{v} {}
    void output(ListRenderer &l, const DowntimeData &downtime) const;

private:
    verbosity verbosity_;
};

template <class T, class U>
struct DowntimeColumn : ListColumn::Callback<T, U> {
    DowntimeColumn(const std::string &name, const std::string &description,
                   const ColumnOffsets &offsets,
                   std::unique_ptr<DowntimeRenderer> renderer,
                   const typename ListColumn::Callback<T, U>::function_type &f)
        : ListColumn::Callback<T, U>{name, description, offsets,
                                     std::move(renderer), f} {}
};

template <>
inline std::string detail::column::serialize(const DowntimeData &data) {
    return std::to_string(data._id);
}
#endif  // DowntimeColumn_h
