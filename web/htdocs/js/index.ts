// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import "core-js/stable";
import "cmk_figures_plugins";

import * as activation from "activation";
import * as ajax from "ajax";
import * as async_progress from "async_progress";
import * as availability from "availability";
import * as background_job from "background_job";
import * as backup from "backup";
import * as bi from "bi";
import * as cmk_figures from "cmk_figures";
import crossfilter from "crossfilter2";
import * as d3 from "d3";
import * as d3Sankey from "d3-sankey";
import * as dashboard from "dashboard";
import * as dc from "dc";
import * as element_dragging from "element_dragging";
import * as foldable_container from "foldable_container";
import * as forms from "forms";
import * as graph_integration from "graph_integration";
import * as graphs from "graphs";
import * as help from "help";
import * as host_diagnose from "host_diagnose";
import * as hover from "hover";
import $ from "jquery";
import * as number_format from "number_format";
import * as page_menu from "page_menu";
import * as password_meter from "password_meter";
import * as popup_menu from "popup_menu";
import * as prediction from "prediction";
import * as profile_replication from "profile_replication";
import * as quicksearch from "quicksearch";
import * as reload_pause from "reload_pause";
import * as selection from "selection";
import * as service_discovery from "service_discovery";
import * as sidebar from "sidebar";
import * as sites from "sites";
import * as sla from "sla";
import * as transfer from "transfer";
import * as utils from "utils";
import * as valuespecs from "valuespecs";
import * as views from "views";
import * as visibility_detection from "visibility_detection";
import * as wato from "wato";
import * as webauthn from "webauthn";

import * as nodevis from "./modules/nodevis/main";

// Optional import is currently not possible using the ES6 imports
let graphs_cee;
let ntop_host_details;
let ntop_alerts;
let ntop_flows;
let ntop_top_talkers;
let ntop_utils;
let license_usage_timeseries_graph;

if (process.env.ENTERPRISE !== "no") {
    require("cmk_figures_plugins_cee");
    graphs_cee = require("graphs_cee");
    ntop_host_details = require("ntop_host_details");
    ntop_alerts = require("ntop_alerts");
    ntop_flows = require("ntop_flows");
    ntop_top_talkers = require("ntop_top_talkers");
    ntop_utils = require("ntop_utils");
    license_usage_timeseries_graph = require("license_usage_timeseries_graph");
} else {
    graphs_cee = null;
    ntop_host_details = null;
    ntop_alerts = null;
    ntop_flows = null;
    ntop_top_talkers = null;
    ntop_utils = null;
    license_usage_timeseries_graph = null;
}

$(() => {
    utils.update_header_timer();
    forms.enable_dynamic_form_elements();
    // TODO: only register when needed?
    element_dragging.register_event_handlers();
});

export const cmk_export = {
    crossfilter: crossfilter,
    d3: d3,
    dc: dc,
    d3Sankey: d3Sankey,
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
        transfer: transfer,
        backup: backup,
        background_job: background_job,
        hover: hover,
        service_discovery: service_discovery,
        sites: sites,
        sidebar: sidebar /* needed for add snapin page */,
        quicksearch: quicksearch,
        host_diagnose: host_diagnose,
        profile_replication: profile_replication,
        wato: wato,
        popup_menu: popup_menu,
        valuespecs: valuespecs,
        number_format: number_format,
        views: views,
        reload_pause: reload_pause,
        graph_integration: graph_integration,
        graphs: graphs,
        graphs_cee: graphs_cee,
        dashboard: dashboard,
        page_menu: page_menu,
        figures: cmk_figures,
        ntop: {
            host_details: ntop_host_details,
            alerts: ntop_alerts,
            flows: ntop_flows,
            top_talkers: ntop_top_talkers,
            utils: ntop_utils,
        },
        license_usage: {
            timeseries_graph: license_usage_timeseries_graph,
        },
        webauthn: webauthn,
        nodevis: nodevis,
    },
};

password_meter.initPasswordStrength();
