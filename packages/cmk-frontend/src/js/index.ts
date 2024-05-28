/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import "core-js/stable";
import "./modules/figures/cmk_figures_plugins";

import crossfilter from "crossfilter2";
import * as d3 from "d3";
import * as d3Sankey from "d3-sankey";
import * as dc from "dc";
import $ from "jquery";

import * as activation from "./modules/activation";
import * as ajax from "./modules/ajax";
import * as async_progress from "./modules/async_progress";
import * as availability from "./modules/availability";
import * as background_job from "./modules/background_job";
import * as backup from "./modules/backup";
import * as bi from "./modules/bi";
import * as dashboard from "./modules/dashboard";
import * as element_dragging from "./modules/element_dragging";
import {figure_registry} from "./modules/figures/cmk_figures";
import * as cmk_figures from "./modules/figures/cmk_figures";
import {EventStats, HostStats, ServiceStats} from "./modules/figures/cmk_stats";
import {TableFigure} from "./modules/figures/cmk_table";
import * as foldable_container from "./modules/foldable_container";
import * as forms from "./modules/forms";
import * as graph_integration from "./modules/graph_integration";
import * as graphs from "./modules/graphs";
import * as help from "./modules/help";
import * as host_diagnose from "./modules/host_diagnose";
import * as hover from "./modules/hover";
import * as jira_issue from "./modules/jira_issue";
import * as keyboard_shortcuts from "./modules/keyboard_shortcuts";
import * as nodevis from "./modules/nodevis/main";
import * as number_format from "./modules/number_format";
import * as page_menu from "./modules/page_menu";
import * as password_meter from "./modules/password_meter";
import * as popup_menu from "./modules/popup_menu";
import * as prediction from "./modules/prediction";
import * as profile_replication from "./modules/profile_replication";
import {render_qr_code} from "./modules/qrcode_rendering";
import * as quicksearch from "./modules/quicksearch";
import * as reload_pause from "./modules/reload_pause";
import * as selection from "./modules/selection";
import * as service_discovery from "./modules/service_discovery";
import * as sidebar from "./modules/sidebar";
import * as sites from "./modules/sites";
import * as sla from "./modules/sla";
import {render_stats_table} from "./modules/tracking_display";
import * as transfer from "./modules/transfer";
import {RequireConfirmation} from "./modules/types";
import * as utils from "./modules/utils";
import * as valuespecs from "./modules/valuespecs";
import * as views from "./modules/views";
import * as visibility_detection from "./modules/visibility_detection";
import * as wato from "./modules/wato";
import * as webauthn from "./modules/webauthn";

// Optional import is currently not possible using the ES6 imports
let graphs_cee;
let ntop_host_details;
let ntop_alerts;
let ntop_flows;
let ntop_top_talkers;
let ntop_utils;
let license_usage_timeseries_graph;
let register;

function registerRawFigureBaseClasses() {
    figure_registry.register(TableFigure);
    figure_registry.register(HostStats);
    figure_registry.register(ServiceStats);
    figure_registry.register(EventStats);
}

registerRawFigureBaseClasses();
if (process.env.ENTERPRISE !== "no") {
    register = require("./modules/cee/register.ts");
    register.registerEnterpriseFigureBaseClasses();
    require("./modules/cee/figures/cmk_figures_plugins_cee");
    graphs_cee = require("./modules/cee/graphs_cee");
    ntop_host_details = require("./modules/cee/ntop/ntop_host_details");
    ntop_alerts = require("./modules/cee/ntop/ntop_alerts");
    ntop_flows = require("./modules/cee/ntop/ntop_flows");
    ntop_top_talkers = require("./modules/cee/ntop/ntop_top_talkers");
    ntop_utils = require("./modules/cee/ntop/ntop_utils");
    license_usage_timeseries_graph = require("./modules/cee/license_usage/license_usage_timeseries_graph");
} else {
    graphs_cee = null;
    ntop_host_details = null;
    ntop_alerts = null;
    ntop_flows = null;
    ntop_top_talkers = null;
    ntop_utils = null;
    license_usage_timeseries_graph = null;
}

type CallableFunctionOptions = {[key: string]: string};
type CallableFunction = (
    node: HTMLElement,
    options: CallableFunctionOptions
) => Promise<void>;

// See cmk.gui.htmllib.generator:KnownTSFunction
// The type on the Python side and the available keys in this dictionary MUST MATCH.
const callable_functions: {[name: string]: CallableFunction} = {
    render_stats_table: render_stats_table,
    render_qr_code: render_qr_code,
};

$(() => {
    utils.update_header_timer();
    forms.enable_dynamic_form_elements();
    // TODO: only register when needed?
    element_dragging.register_event_handlers();
    keyboard_shortcuts.register_shortcuts();
    // add a confirmation popup for each for that has a valid confirmation text

    // See cmk.gui.htmllib.generator:HTMLWriter.call_ts_function
    document
        .querySelectorAll<HTMLElement>("*[data-cmk_call_ts_function]")
        .forEach((container, _) => {
            const data = container.dataset;
            const function_name: string = data.cmk_call_ts_function!;
            let options: CallableFunctionOptions;
            if (data.cmk_call_ts_options) {
                options = JSON.parse(data.cmk_call_ts_options);
            } else {
                options = {};
            }
            const ts_function = callable_functions[function_name];
            // The function has the responsibility to take the container and do it's thing with it.
            ts_function(container, options);
        });

    document
        .querySelectorAll<HTMLFormElement>("form[data-cmk_form_confirmation]")
        .forEach((form, _) => {
            const confirmation: RequireConfirmation = JSON.parse(
                form.dataset.cmk_form_confirmation!
            );
            forms.add_confirm_on_submit(form, confirmation);
        });
});

export const cmk_export = {
    crossfilter: crossfilter,
    d3: d3,
    dc: dc,
    d3Sankey: d3Sankey,
    cmk: {
        activation: activation,
        ajax: ajax,
        async_progress: async_progress,
        availability: availability,
        background_job: background_job,
        backup: backup,
        bi: bi,
        dashboard: dashboard,
        element_dragging: element_dragging,
        figures: cmk_figures,
        foldable_container: foldable_container,
        forms: forms,
        graph_integration: graph_integration,
        graphs: graphs,
        graphs_cee: graphs_cee,
        help: help,
        host_diagnose: host_diagnose,
        hover: hover,
        jira_issue: jira_issue,
        keyboard_shortcuts: keyboard_shortcuts,
        license_usage: {
            timeseries_graph: license_usage_timeseries_graph,
        },
        nodevis: nodevis,
        ntop: {
            host_details: ntop_host_details,
            alerts: ntop_alerts,
            flows: ntop_flows,
            top_talkers: ntop_top_talkers,
            utils: ntop_utils,
        },
        number_format: number_format,
        page_menu: page_menu,
        popup_menu: popup_menu,
        prediction: prediction,
        profile_replication: profile_replication,
        quicksearch: quicksearch,
        reload_pause: reload_pause,
        render_stats_table: render_stats_table,
        selection: selection,
        service_discovery: service_discovery,
        sidebar: sidebar /* needed for add snapin page */,
        sites: sites,
        sla: sla,
        transfer: transfer,
        utils: utils,
        valuespecs: valuespecs,
        views: views,
        visibility_detection: visibility_detection,
        wato: wato,
        webauthn: webauthn,
    },
};

password_meter.initPasswordStrength();
