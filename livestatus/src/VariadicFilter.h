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

#ifndef VariadicFilter_h
#define VariadicFilter_h

#include "config.h"  // IWYU pragma: keep
#include <cstddef>
#include <deque>
#include <memory>
#include <string>
#include "Filter.h"
class FilterVisitor;

enum class LogicalOperator { and_, or_ };

class VariadicFilter : public Filter {
public:
    static std::unique_ptr<VariadicFilter> make(LogicalOperator logicOp);
    void accept(FilterVisitor &v) const override;
    void addSubfilter(std::unique_ptr<Filter> f);
    std::unique_ptr<Filter> stealLastSubfiler();
    void combineFilters(int count, LogicalOperator andor);
    size_t size() const { return _subfilters.size(); }
    auto begin() const { return _subfilters.begin(); }
    auto end() const { return _subfilters.end(); }
    void findIntLimits(const std::string &colum_nname, int *lower, int *upper,
                       int timezone_offset) const override;

protected:
    std::deque<std::unique_ptr<Filter>> _subfilters;
};

#endif  // VariadicFilter_h
