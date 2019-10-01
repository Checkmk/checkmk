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
// tails.  You should have received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import * as utils from "utils";

export function details_period_hover(td, sla_period, onoff)
{
    if (utils.has_class(td, "lock_hilite")) {
        return;
    }

    var sla_period_elements = document.getElementsByClassName(sla_period);
    for(var i = 0; i < sla_period_elements.length; i++)
    {
        if (onoff) {
            utils.add_class(sla_period_elements[i], "sla_hilite");
        }
        else {
            utils.remove_class(sla_period_elements[i], "sla_hilite");
        }
    }
}


export function details_period_click(td, sla_period)
{
    var sla_period_elements = document.getElementsByClassName(sla_period);
    var onoff = utils.has_class(td, "lock_hilite");
    for(var i = 0; i < sla_period_elements.length; i++)
    {
        if (onoff) {
            utils.remove_class(sla_period_elements[i], "sla_hilite");
            utils.remove_class(sla_period_elements[i], "lock_hilite");
        }
        else {
            utils.add_class(sla_period_elements[i], "sla_hilite");
            utils.add_class(sla_period_elements[i], "lock_hilite");
        }
    }
}


export function details_table_hover(tr, row_id, onoff) {
    var sla_period_elements = tr.closest("table").closest("tbody").getElementsByClassName(row_id);
    for(var i = 0; i < sla_period_elements.length; i++)
    {

        if (onoff) {
            utils.add_class(sla_period_elements[i], "sla_hilite");
            utils.add_class(sla_period_elements[i], "sla_error_hilite");
        }
        else {
            utils.remove_class(sla_period_elements[i], "sla_error_hilite");
            if (!utils.has_class(sla_period_elements[i], "lock_hilite")) {
                utils.remove_class(sla_period_elements[i], "sla_hilite");
            }
        }
    }
}
