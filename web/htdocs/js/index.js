// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import "core-js/stable";

import $ from "jquery";
import * as d3 from "d3";
import * as d3_sankey from "d3-sankey";
import * as crossfilter from "crossfilter2";
import * as dc from "dc";
import * as forms from "forms";
import * as ajax from "ajax";
import * as prediction from "prediction";
import * as utils from "utils";
import * as foldable_container from "foldable_container";
import * as visibility_detection from "visibility_detection";
import * as async_progress from "async_progress";
import * as activation from "activation";
import * as selection from "selection";
import * as element_dragging from "element_dragging";
import * as help from "help";
import * as availability from "availability";
import * as sla from "sla";
import * as bi from "bi";
import * as crash_reporting from "crash_reporting";
import * as backup from "backup";
import * as hover from "hover";
import * as service_discovery from "service_discovery";
import * as sidebar from "sidebar";
import * as sites from "sites";
import * as host_diagnose from "host_diagnose";
import * as profile_replication from "profile_replication";
import * as wato from "wato";
import * as popup_menu from "popup_menu";
import * as valuespecs from "valuespecs";
import * as views from "views";
import * as reload_pause from "reload_pause";
import * as graph_integration from "graph_integration";
import * as dashboard from "dashboard";
import * as page_menu from "page_menu";

import * as cmk_figures from "cmk_figures";
import "cmk_figures_plugins";

import * as cmk_tabs from "cmk_tabs";

import * as node_visualization from "node_visualization";
import * as node_visualization_utils from "node_visualization_utils";
import * as node_visualization_layout_styles from "node_visualization_layout_styles";
import * as node_visualization_viewport_utils from "node_visualization_viewport_utils";
import * as node_visualization_viewport_layers from "node_visualization_viewport_layers";

import {fetch} from "whatwg-fetch";

// Optional import is currently not possible using the ES6 imports
var graphs;
try {
    graphs = require("graphs");
} catch (e) {
    graphs = null;
}

var ntop_host_details;
try {
    ntop_host_details = require("ntop_host_details");
} catch (e) {
    ntop_host_details = null;
}

var ntop_alerts;
try {
    ntop_alerts = require("ntop_alerts");
} catch (e) {
    ntop_alerts = null;
}

var ntop_flows;
try {
    ntop_flows = require("ntop_flows");
} catch (e) {
    ntop_flows = null;
}

$(() => {
    utils.update_header_timer();
    forms.enable_dynamic_form_elements();
    // TODO: only register when needed?
    element_dragging.register_event_handlers();
});

export const cmk_export = {
    crossfilter: crossfilter.default,
    d3: d3,
    dc: dc,
    sankey: d3_sankey,
    cmk: {
        forms: forms,
        prediction: prediction,
        ajax: ajax,
        utils: utils,
        foldable_container: foldable_container,
        visibility_detection: visibility_detection,
        async_progress: async_progress,
        activation: activation,
        selection: selection,
        element_dragging: element_dragging,
        help: help,
        availability: availability,
        sla: sla,
        bi: bi,
        crash_reporting: crash_reporting,
        backup: backup,
        hover: hover,
        service_discovery: service_discovery,
        sites: sites,
        sidebar: sidebar /* needed for add snapin page */,
        host_diagnose: host_diagnose,
        profile_replication: profile_replication,
        wato: wato,
        popup_menu: popup_menu,
        valuespecs: valuespecs,
        views: views,
        reload_pause: reload_pause,
        graph_integration: graph_integration,
        graphs: graphs,
        dashboard: dashboard,
        page_menu: page_menu,
        // TODO: node_visualization cleanups
        node_visualization_utils: node_visualization_utils,
        node_visualization_layout_styles: node_visualization_layout_styles,
        node_visualization_viewport_utils: node_visualization_viewport_utils,
        node_visualization_viewport_layers: node_visualization_viewport_layers,
        node_visualization: node_visualization,
        figures: cmk_figures,
        tabs: cmk_tabs,
        ntop: {
            host_details: ntop_host_details,
            alerts: ntop_alerts,
            flows: ntop_flows,
        },
    },
};
