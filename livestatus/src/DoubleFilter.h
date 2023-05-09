// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DoubleFilter_h
#define DoubleFilter_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <functional>
#include <memory>
#include <string>

#include "ColumnFilter.h"
#include "Filter.h"
#include "contact_fwd.h"
#include "opids.h"
class Logger;
class Row;

class DoubleFilter : public ColumnFilter {
public:
    DoubleFilter(Kind kind, std::string columnName, std::function<double(Row)>,
                 RelationalOperator relOp, const std::string &value, Logger *);
    bool accepts(Row row, const contact *auth_user,
                 std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::unique_ptr<Filter> copy() const override;
    [[nodiscard]] std::unique_ptr<Filter> negate() const override;
    [[nodiscard]] Logger *logger() const;

private:
    std::function<double(Row)> _getValue;
    const double _ref_value;
    Logger *const _logger;
};

#endif  // DoubleFilter_h
