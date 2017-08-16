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

#ifndef OffsetStringMacroColumn_h
#define OffsetStringMacroColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include <string>
#include "OffsetStringColumn.h"
#include "contact_fwd.h"
#include "nagios.h"
#include "opids.h"
class Filter;
class Row;
class RowRenderer;

class OffsetStringMacroColumn : public OffsetStringColumn {
public:
    OffsetStringMacroColumn(const std::string &name,
                            const std::string &description, int offset,
                            int indirect_offset, int extra_offset,
                            int extra_extra_offset)
        : OffsetStringColumn(name, description, offset, indirect_offset,
                             extra_offset, extra_extra_offset) {}
    // reimplement several functions from StringColumn

    void output(Row row, RowRenderer &r,
                const contact *auth_user) const override;
    std::unique_ptr<Filter> createFilter(
        RelationalOperator relOp, const std::string &value) const override;

    // overriden by host and service macro columns
    virtual host *getHost(Row) const = 0;
    virtual service *getService(Row) const = 0;

private:
    const char *expandMacro(const char *macroname, host *hst,
                            service *svc) const;
    const char *expandCustomVariables(const char *varname,
                                      customvariablesmember *custvars) const;
};

#endif  // OffsetStringMacroColumn_h
