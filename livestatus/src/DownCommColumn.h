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

#ifndef DownCommColumn_h
#define DownCommColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include <string>
#include "ListColumn.h"
#include "nagios.h"
class DowntimeOrComment;
class DowntimesOrComments;
class RowRenderer;

class DownCommColumn : public ListColumn {
    const DowntimesOrComments &_holder;
    bool _is_downtime;
    bool _with_info;
    bool _is_service;       // and not host
    bool _with_extra_info;  // provides date and type

    bool match(DowntimeOrComment *dt, void *data);

public:
    DownCommColumn(const std::string &name, const std::string &description,
                   int indirect_offset, const DowntimesOrComments &holder,
                   bool is_downtime, bool is_service, bool with_info,
                   bool with_extra_info, int extra_offset = -1)
        : ListColumn(name, description, indirect_offset, extra_offset)
        , _holder(holder)
        , _is_downtime(is_downtime)
        , _with_info(with_info)
        , _is_service(is_service)
        , _with_extra_info(with_extra_info) {}
    std::unique_ptr<Contains> makeContains(const std::string &name) override;
    void output(void *row, RowRenderer &r, contact *auth_user) override;
    bool isEmpty(void *data) override;
};

#endif  // DownCommColumn_h
