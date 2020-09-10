// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ListAttributesColumn_h
#define ListAttributesColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <memory>
#include <string>
#include <utility>

#include "Column.h"
#include "CustomVarsDictColumn.h"
#include "Filter.h"
#include "MonitoringCore.h"
#include "opids.h"
class Aggregator;
enum class AttributeKind;
class Row;
class RowRenderer;

#ifdef CMC
#include "contact_fwd.h"
#else
// TODO(sp) Why on earth is "contact_fwd.h" not enough???
#include "nagios.h"
#endif

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the empty Attributes.
template <class T>
class AttributesLambdaColumn : public CustomVarsDictColumn {
public:
    AttributesLambdaColumn(std::string name, std::string description,
                           const ColumnOffsets& offsets,
                           std::function<Attributes(const T&)> f)
        : CustomVarsDictColumn(
              std::move(name), std::move(description), offsets,
              // TODO(ml): The hierarchy of every *LambdaColumn is wrong anyway
              // but this is the easiest way to get rid of the pointer
              // arithmetic by replacing inheritance with delegation without
              // breaking anything. So here we make the "base" ctor happy with a
              // few more junk args.
              nullptr, AttributeKind::tags)
        , get_value_{std::move(f)} {}

    ~AttributesLambdaColumn() override = default;

    [[nodiscard]] Attributes getValue(Row row) const override {
        const T* data = columnData<T>(row);
        return data == nullptr ? Attributes{} : get_value_(*data);
    }

private:
    std::function<Attributes(const T&)> get_value_;
};

#endif
