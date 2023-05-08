// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Aggregator_h
#define Aggregator_h

#include "config.h"  // IWYU pragma: keep

#include <cmath>
#include <functional>

#include "Renderer.h"
#include "Row.h"
#include "contact_fwd.h"
class Query;

class Aggregation {
public:
    virtual ~Aggregation() = default;
    virtual void update(double value) = 0;
    [[nodiscard]] virtual double value() const = 0;
};

class Aggregator {
public:
    virtual ~Aggregator() = default;
    virtual void consume(Row row, const contact *auth_user,
                         std::chrono::seconds timezone_offset) = 0;
    virtual void output(RowRenderer &r) const = 0;
};

#endif  // Aggregator_h
