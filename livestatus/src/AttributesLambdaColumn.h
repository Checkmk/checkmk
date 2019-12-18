// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

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

class AttributesLambdaColumn : public CustomVarsDictColumn {
public:
    AttributesLambdaColumn(std::string name, std::string description,
                           std::function<Attributes(Row)> f)
        : CustomVarsDictColumn(
              std::move(name), std::move(description), {},
              // TODO(ml): The hierarchy of every *LambdaColumn is wrong anyway
              // but this is the easiest way to get rid of the pointer
              // arithmetic by replacing inheritance with delegation without
              // breaking anything. So here we make the "base" ctor happy with a
              // few more junk args.
              nullptr, AttributeKind::tags)
        , get_value_{f} {}
    virtual ~AttributesLambdaColumn() = default;
    Attributes getValue(Row row) const override { return get_value_(row); }

private:
    std::function<Attributes(Row)> get_value_;
};

#endif
