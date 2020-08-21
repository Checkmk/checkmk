// Copyright (C) 2019 tribe29 GmbH - License: Check_MK Enterprise License
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StringPerfdataColumn_h
#define StringPerfdataColumn_h

#include "config.h"  // IWYU pragma: keep

#include <memory>

#include "Column.h"
#include "PerfdataAggregator.h"
#include "StringLambdaColumn.h"
class Aggregator;

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the empty string.
template <class T>
class StringPerfdataColumn : public StringLambdaColumn<T> {
public:
    using StringLambdaColumn<T>::StringLambdaColumn;

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<PerfdataAggregator>(factory, this);
    }
};

#endif  // StringPerfdataColumn_h
