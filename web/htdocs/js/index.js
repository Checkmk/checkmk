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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import $ from "jquery";
import * as forms from "forms";
import * as ajax from "ajax";
import * as prediction from "prediction";
import * as utils from "utils";
import * as foldable_container from "foldable_container";
import * as visibility_detection from "visibility_detection";
import * as async_progress from "async_progress";
import * as activation from "activation";
import * as selection from "selection";
import * as dashboard from "dashboard";

require("script-loader!./checkmk.js");
require("colorpicker");
require("script-loader!./wato.js");

// TODO: Find a better solution for this CEE specific include
try {
    require("script-loader!../../../enterprise/web/htdocs/js/graphs.js");
} catch(e) {} // eslint-disable-line no-empty

$(() => {
    forms.enable_select2();
});

export default {
    cmk: {
        prediction: prediction,
        ajax: ajax,
        utils: utils,
        foldable_container: foldable_container,
        visibility_detection: visibility_detection,
        async_progress: async_progress,
        activation: activation,
        selection: selection,
        dashboard: dashboard
    },
    // TODO: Compatibility for not yet modularized JS code
    executeJSbyObject: utils.execute_javascript_by_object,
    executeJS: utils.execute_javascript_by_id,
    getTarget: utils.get_target,
    getButton: utils.get_button,
    prevent_default_events: utils.prevent_default_events,
    has_class: utils.has_class,
    remove_class: utils.remove_class,
    add_class: utils.add_class,
    change_class: utils.change_class,
    get_url: ajax.get_url,
    post_url: ajax.post_url,
    call_ajax: ajax.call_ajax
};
