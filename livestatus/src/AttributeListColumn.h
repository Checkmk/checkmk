// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef AttributeListColumn_h
#define AttributeListColumn_h

#include "config.h"  // IWYU pragma: keep

#include <cstddef>
#include <memory>
#include <string>
#include <vector>

#include "Filter.h"
#include "ListColumn.h"
#include "Row.h"
#include "opids.h"
class IntFilter;
class Logger;

namespace column::attribute_list {
struct AttributeBit {
    AttributeBit(std::size_t i, bool v) : index{i}, value{v} {}
    std::size_t index;
    bool value;
};
inline bool operator==(const AttributeBit &x, const AttributeBit &y) {
    return x.index == y.index && x.value == y.value;
}
std::string refValueFor(const std::string &value, Logger *logger);
unsigned long decode(const std::vector<AttributeBit> &mask);
std::vector<AttributeBit> encode(unsigned long mask);
std::vector<AttributeBit> encode(const std::vector<std::string> &strs);
}  // namespace column::attribute_list

namespace column::detail {
template <>
std::string serialize(const column::attribute_list::AttributeBit &bit);
}  // namespace column::detail

template <class T, class U>
class AttributeListColumn : public ListColumn<T, U> {
public:
    using ListColumn<T, U>::ListColumn;
    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<IntFilter>(
            kind, this->name(),
            [this](Row row) {
                return column::attribute_list::decode(
                    column::attribute_list::encode(
                        this->getValue(row, nullptr, {})));
            },
            relOp, column::attribute_list::refValueFor(value, this->logger()));
    }
};

#endif
