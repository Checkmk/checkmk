
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

import "forms";
import * as ajax from "ajax";
import * as utils from "utils";
import * as foldable_container from "foldable_container";
import * as sidebar from "sidebar";
import * as quicksearch from "quicksearch";
import * as visibility_detection from "visibility_detection";
import * as valuespecs from "valuespecs";

export const cmk_export = {
    get_url: ajax.get_url,
    post_url: ajax.post_url,
    call_ajax: ajax.call_ajax,
    cmk: {
        ajax: ajax,
        sidebar: sidebar,
        utils: utils,
        foldable_container: foldable_container,
        quicksearch: quicksearch,
        visibility_detection: visibility_detection,
        valuespecs: valuespecs
    }
};
