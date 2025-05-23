/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import "core-js/stable";
import "./modules/figures/cmk_figures_plugins";

/* eslint-disable import/no-namespace -- Needed for exports */
import crossfilter from "crossfilter2";
import * as d3 from "d3";
import * as d3Sankey from "d3-sankey";
import $ from "jquery";

import * as activation from "./modules/activation";
import * as ajax from "./modules/ajax";
import * as async_progress from "./modules/async_progress";
import * as availability from "./modules/availability";
import * as background_job from "./modules/background_job";
import * as backup from "./modules/backup";
import * as bi from "./modules/bi";
import * as callable_functions from "@/modules/callable_functions";
import * as dashboard from "./modules/dashboard";
import * as element_dragging from "./modules/element_dragging";
import * as cmk_figures from "./modules/figures/cmk_figures";
import {register} from "./modules/figures/register";
import * as foldable_container from "./modules/foldable_container";
import * as forms from "./modules/forms";
import * as graph_integration from "./modules/graph_integration";
import * as graphs from "./modules/graphs";
import * as graphs_cee from "./modules/graphs_cee";
import * as help from "./modules/help";
import * as host_diagnose from "./modules/host_diagnose";
import * as hover from "./modules/hover";
import * as main_menu_shortcut_handler from "./modules/main_menu_shortcut_handler";
import * as license_usage_timeseries_graph from "./modules/license_usage/license_usage_timeseries_graph";
import * as nodevis from "./modules/nodevis/main";
import * as ntop_alerts from "./modules/ntop/ntop_alerts";
import * as ntop_flows from "./modules/ntop/ntop_flows";
import * as ntop_host_details from "./modules/ntop/ntop_host_details";
import * as ntop_top_talkers from "./modules/ntop/ntop_top_talkers";
import * as ntop_utils from "./modules/ntop/ntop_utils";
import * as number_format from "./modules/number_format";
import * as page_menu from "./modules/page_menu";
import {initPasswordStrength} from "./modules/password_meter";
import * as popup_menu from "./modules/popup_menu";
import * as prediction from "./modules/prediction";
import * as profile_replication from "./modules/profile_replication";
import * as quicksearch from "./modules/quicksearch";
import * as reload_pause from "./modules/reload_pause";
import * as selection from "./modules/selection";
import * as service_discovery from "./modules/service_discovery";
import * as sidebar from "./modules/sidebar";
import * as sites from "./modules/sites";
import * as sla from "./modules/sla";
import {render_stats_table} from "./modules/tracking_display";
import * as transfer from "./modules/transfer";
import type {RequireConfirmation} from "./modules/types";
import * as utils from "./modules/utils";
import * as valuespecs from "./modules/valuespecs";
import * as views from "./modules/views";
import * as visibility_detection from "./modules/visibility_detection";
import * as wato from "./modules/wato";
import * as webauthn from "./modules/webauthn";
import {getKeyShortcutServiceInstance} from "./modules/keyShortcuts";

register();

$(() => {
    utils.update_header_timer();
    forms.enable_dynamic_form_elements();
    // TODO: only register when needed?
    element_dragging.register_event_handlers();

    const keyShortcuts = getKeyShortcutServiceInstance();
    main_menu_shortcut_handler.register_shortcuts(keyShortcuts);

    // add a confirmation popup for each for that has a valid confirmation text
    callable_functions.init_callable_ts_functions(document);

    document
        .querySelectorAll<HTMLFormElement>("form[data-cmk_form_confirmation]")
        .forEach((form, _) => {
            const confirmation: RequireConfirmation = JSON.parse(
                form.dataset.cmk_form_confirmation!,
            );
            forms.add_confirm_on_submit(form, confirmation);
        });
});

export const cmk_export = {
    crossfilter: crossfilter,
    d3: d3,
    d3Sankey: d3Sankey,
    cmk: {
        activation: activation,
        ajax: ajax,
        async_progress: async_progress,
        availability: availability,
        background_job: background_job,
        backup: backup,
        bi: bi,
        d3: d3,
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

initPasswordStrength();
