/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {TextFigureData} from "@/modules/figures/cmk_figures";
import {TextFigure} from "@/modules/figures/cmk_figures";
import {
    background_status_component,
    getIn,
    metric_value_component,
    metric_value_component_options_big_centered_text,
    svc_status_css,
} from "@/modules/figures/cmk_figures_utils";

interface StateFigureDataData {
    url: string;
    //from cmk.gui.dashboard.dashlet.dashlets.status_helpers.service_table_query
    service_state: any;
    service_has_been_checked: any;
    service_description: string;
    host_name: string;
}

interface StateFigureDataPlotDefinition {
    id: string;
    plot_type: string;
    status_display: Record<string, string | null>;
}

interface StateFigureData
    extends TextFigureData<StateFigureDataData, StateFigureDataPlotDefinition> {
    data: StateFigureDataData[];
}

export class StateFigure extends TextFigure<StateFigureData> {
    getEmptyData() {
        return {
            data: [],
            plot_definitions: [],
            title: "",
            title_url: "",
        };
    }

    override ident() {
        return "state_service";
    }

    override render() {
        const plot = this._data.plot_definitions[0];
        if (!plot) {
            // rendering before the first ajax call
            return;
        }

        this.render_title(this._data.title, this._data.title_url!);

        const svc_status_display = getIn(plot, "status_display");
        const is_ok_status = (getIn(svc_status_display, "css") || "").endsWith(
            "0",
        );

        const background_status_cls = svc_status_css(
            "background",
            svc_status_display,
        );
        const label_paint_style = getIn(svc_status_display, "paint");

        svc_status_css(label_paint_style, svc_status_display);

        const summary_visible =
            !is_ok_status && getIn(svc_status_display, "summary") === "not_ok";

        background_status_component(this.plot, {
            size: this.plot_size,
            css_class: background_status_cls,
            visible: background_status_cls !== "",
        });

        const margin = 15;
        const font_size = 14; // defined in cmk_figures.state_component

        // potential long summary text starting at the top of dashlet
        const summary_data = summary_visible ? this._data.data : [];
        const margin_bottom = font_size * 2; // space for label at the bottom

        // metric_value_component creates a href, so we want to link the label and status text, too:
        this.plot
            .selectAll("a.href")
            .data(summary_data)
            .join("a")
            .classed("href", true)
            // @ts-ignore
            .attr("xlink:href", d => d.url || null)
            .selectAll("foreignObject")
            .data(d => [d])
            .join("foreignObject")
            .style("position", "relative")
            .attr("x", margin)
            .attr("y", this.plot_size.height * 0.5 + margin_bottom)
            .attr("width", this.plot_size.width - margin * 2)
            .attr("height", this.plot_size.height * 0.5 - margin_bottom * 2)
            .selectAll("div")
            .data(d => [d])
            .join("xhtml:div")
            .style("position", "absolute")
            .style("bottom", 0)
            .style("width", "100%")
            .style("font-size", font_size + "px")
            .style("text-align", "center")
            .style("overflow-wrap", "break-word") // break long words
            // @ts-ignore
            .text(d => d.plugin_output);

        // big short status display center of dashlet
        metric_value_component(this.plot, {
            value: {
                value: svc_status_display.msg,
                url: this._data.data[0].url,
            },
            ...metric_value_component_options_big_centered_text(
                this.plot_size,
                {},
            ),
        });
    }
}

interface StateHostFigureDataData {
    url: string;
    host_state: any;
    host_has_been_checked: any;
    host_description: string;
    host_name: string;
}

type StateHostFigureDataPlotDefinition = StateFigureDataPlotDefinition;

//This type is not used for now, because this causes other errors related to figure data.
//But it should be used in the future to specify the Data type of StateHostFigure
interface _StateHostFigureData
    extends TextFigureData<
        StateHostFigureDataData,
        StateHostFigureDataPlotDefinition
    > {
    data: StateHostFigureDataData[];
}

export class StateHostFigure extends StateFigure {
    override ident() {
        return "state_host";
    }
}
