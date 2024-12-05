/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "@/modules/ajax";

import {ForceConfig} from "./force_utils";
import type {
    SerializedNodevisLayout,
    StyleOptionSpecRange,
} from "./layout_utils";
import {get} from "./texts";
import type {d3SelectionDiv, NodevisWorld} from "./type_defs";
import {render_save_delete} from "./utils";

export class LayoutAggregations {
    _world: NodevisWorld;

    constructor(world: NodevisWorld) {
        this._world = world;
    }

    render_layout(selection: d3SelectionDiv): void {
        this._render_aggregation_configuration(selection);
    }

    save_layout_for_aggregation(layout_config: {
        [name: string]: SerializedNodevisLayout;
    }): void {
        call_ajax("ajax_save_bi_aggregation_layout.py", {
            method: "POST",
            post_data:
                "layout=" + encodeURIComponent(JSON.stringify(layout_config)),
            response_handler: () => {
                this._world.datasource_manager.schedule(true);
            },
        });
    }

    delete_layout_for_aggregation(aggregation_name: string) {
        call_ajax("ajax_delete_bi_aggregation_layout.py", {
            method: "POST",
            post_data:
                "aggregation_name=" + encodeURIComponent(aggregation_name),
            response_handler: () => {
                this._world.datasource_manager.schedule(true);
            },
        });
    }

    _save_explicit_layout_clicked() {
        const layout_config = this._world.viewport
            .get_layout_manager()
            .get_layout()
            .serialize();
        const new_layout: Record<string, SerializedNodevisLayout> = {};
        const aggr_name = this._world.viewport.get_all_nodes()[0].data.name;
        new_layout[aggr_name] = layout_config;
        this.save_layout_for_aggregation(new_layout);
    }

    _delete_explicit_layout_clicked() {
        const aggr_name = this._world.viewport.get_all_nodes()[0].data.name;
        this.delete_layout_for_aggregation(aggr_name);
    }

    _render_aggregation_configuration(selection: d3SelectionDiv): void {
        const aggr_name =
            this._world.viewport.get_all_nodes()[0].data.name || "Missing data";
        const layout =
            this._world.viewport.get_layout_manager().get_layout() || {};
        const origin_info = layout.origin_info || "Missing data";

        const table = selection
            .selectAll("table#layout_settings")
            .data([null])
            .join(enter =>
                enter
                    .insert("table", "div.radio_group")
                    .attr("id", "layout_settings"),
            );

        table
            .selectAll<HTMLTableRowElement, unknown>("tr.info")
            .data(
                [
                    [["Aggregation name"], [aggr_name]],
                    [["Layout origin"], [origin_info]],
                ],
                // @ts-ignore
                d => d[0],
            )
            .join("tr")
            .classed("info", true)
            .selectAll("td")
            .data(d => d)
            .join("td")
            .text(d => {
                return d[0];
            });

        const buttons: [string, string, string, () => void][] = [
            [
                get("save"),
                "button save_delete save",
                get("save_aggregation"),
                () => this._save_explicit_layout_clicked(),
            ],
            [
                get("delete_layout"),
                "button save_delete delete",
                "",
                () => this._delete_explicit_layout_clicked(),
            ],
        ];
        render_save_delete(selection, buttons);
    }
}

export class BIForceConfig extends ForceConfig {
    override description = "BI Force configuration";

    override get_style_options(): StyleOptionSpecRange[] {
        return [
            {
                id: "center",
                values: {default: 0.05, min: -0.08, max: 1, step: 0.01},
                option_type: "range",
                text: "Center force strength",
            },
            {
                id: "charge",
                values: {default: -300, min: -1000, max: 50, step: 1},
                option_type: "range",
                text: "Repulsion force leaf",
            },
            {
                id: "charge_aggregator",
                values: {default: -300, min: -1000, max: 50, step: 1},
                option_type: "range",
                text: "Repulsion force branch",
            },
            {
                id: "link_distance",
                values: {default: 30, min: -10, max: 300, step: 1},
                option_type: "range",
                text: "Link distance leaf",
            },
            {
                id: "link_distance_aggregator",
                values: {default: 30, min: -10, max: 300, step: 1},
                option_type: "range",
                text: "Link distance branch",
            },
            {
                id: "link_strength",
                values: {default: 0.3, min: 0, max: 2, step: 0.01},
                option_type: "range",
                text: "Link strength",
            },
            {
                id: "collide",
                values: {default: 15, min: 0, max: 150, step: 1},
                option_type: "range",
                text: "Collision box leaf",
            },
            {
                id: "collision_force_aggregator",
                values: {default: 15, min: 0, max: 150, step: 1},
                option_type: "range",
                text: "Collision box branch",
            },
        ];
    }
}
