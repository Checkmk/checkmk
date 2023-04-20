// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/CountAggregator.h"

#include "livestatus/Filter.h"
#include "livestatus/Renderer.h"
#include "livestatus/Row.h"

void CountAggregator::consume(Row row, const User &user,
                              std::chrono::seconds timezone_offset) {
    if (_filter->accepts(row, user, timezone_offset)) {
        _count++;
    }
}

void CountAggregator::output(RowRenderer &r) const { r.output(_count); }
