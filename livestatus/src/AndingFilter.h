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

#ifndef AndingFilter_h
#define AndingFilter_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>
#include "VariadicFilter.h"
#include "contact_fwd.h"
class Filter;
class FilterVisitor;
class Row;

class AndingFilter : public VariadicFilter {
public:
    void accept(FilterVisitor &v) const override;
    bool accepts(Row row, const contact *auth_user,
                 std::chrono::seconds timezone_offset) const override;
    void findIntLimits(const std::string &colum_nname, int *lower, int *upper,
                       std::chrono::seconds timezone_offset) const override;
    bool optimizeBitmask(const std::string &column_name, uint32_t *mask,
                         std::chrono::seconds timezone_offset) const override;
    std::unique_ptr<Filter> copy() const override;
    std::unique_ptr<Filter> negate() const override;
    const std::string *findValueForIndexing(
        const std::string &column_name) const;
    std::unique_ptr<Filter> stealLastSubFilter();
    size_t size() const { return _subfilters.size(); }
    auto begin() const { return _subfilters.begin(); }
    auto end() const { return _subfilters.end(); }
};

#endif  // AndingFilter_h
