/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {zoomIdentity} from "d3";

import {figure_registry} from "@/modules/figures/cmk_figures";
import type {
    ElementSize,
    SingleGraphDashletConfig,
} from "@/modules/figures/figure_types";

import {TimeseriesFigure} from "./cmk_timeseries";

// A single metric figure with optional graph rendering in the background
export class SingleMetricFigure extends TimeseriesFigure<SingleGraphDashletConfig> {
    override ident() {
        return "single_metric";
    }

    constructor(div_selector: string, fixed_size: ElementSize) {
        super(div_selector, fixed_size);
        this.margin = {top: 0, right: 0, bottom: 0, left: 0};
    }

    override initialize() {
        super.initialize();
        this.lock_zoom_x = true;
        this.lock_zoom_y = true;
        this.lock_zoom_x_scale = true;
    }

    override _adjust_margin() {
        this.margin.top -= 8; // it has no timeseries y-labels scale
    }

    override _setup_zoom() {
        this._current_zoom = zoomIdentity;
    }

    override update_domains() {
        TimeseriesFigure.prototype.update_domains.call(this);
        const display_range = this._dashlet_spec.display_range;
        // display_range could be null, or [str, [int, int]]
        if (Array.isArray(display_range) && display_range[0] === "fixed") {
            this._y_domain = display_range[1][1];
            this.orig_scale_y.domain(this._y_domain);
        }
    }

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    override render_legend() {}

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    override render_grid() {}

    override render_axis() {
        const toggle_range_display = this._dashlet_spec.toggle_range_display;
        if (
            this._subplots.filter(d => d.definition!.plot_type == "area")
                .length == 0 ||
            !toggle_range_display
        ) {
            this.g.selectAll("text.range").remove();
            return;
        }

        const render_function = this.get_scale_render_function();
        const domain = this._y_domain;

        const domain_labels = [
            {
                value: render_function(domain[0]),
                y: this.plot_size.height - 7,
                x: 5,
            },
            {
                value: render_function(domain[1]),
                y: 15,
                x: 5,
            },
        ];

        this.g
            .selectAll("text.range")
            .data(domain_labels)
            .join("text")
            .classed("range", true)
            .text(d => d.value)
            .style("font-size", "10pt")
            .attr("x", d => d.x)
            .attr("y", d => d.y);
    }
}

figure_registry.register(SingleMetricFigure);
