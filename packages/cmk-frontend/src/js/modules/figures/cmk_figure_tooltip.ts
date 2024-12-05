/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {BaseType, Selection} from "d3";
import {pointer, select} from "d3";

interface FigureTooltipElementSize {
    width: null | number;
    height: null | number;
}

// Class which handles the display of a tooltip
// It generates basic tooltips and handles its correct positioning
export class FigureTooltip {
    _tooltip: Selection<HTMLDivElement, unknown, BaseType, unknown>;
    figure_size: FigureTooltipElementSize;
    plot_size: FigureTooltipElementSize;

    constructor(
        tooltip_selection: Selection<
            HTMLDivElement,
            unknown,
            BaseType,
            unknown
        >,
    ) {
        this._tooltip = tooltip_selection;
        this._tooltip
            .style("opacity", 0)
            .style("position", "absolute")
            .classed("tooltip", true);
        this.figure_size = {width: null, height: null};
        this.plot_size = {width: null, height: null};
    }

    update_sizes(
        figure_size: FigureTooltipElementSize,
        plot_size: FigureTooltipElementSize,
    ) {
        this.figure_size = figure_size;
        this.plot_size = plot_size;
    }

    update_position(event: MouseEvent) {
        if (!this.active()) return;

        const tooltip_size = {
            width: this._tooltip.node()!.offsetWidth,
            height: this._tooltip.node()!.offsetHeight,
        };

        const [x, y] = pointer(
            event,
            (event.target as HTMLDivElement).closest("svg"),
        );

        const is_at_right_border =
            event.pageX >= document.body.clientWidth - tooltip_size.width;
        const is_at_bottom_border =
            event.pageY >= document.body.clientHeight - tooltip_size.height;

        const left = is_at_right_border
            ? x - tooltip_size.width + "px"
            : x + "px";
        const top = is_at_bottom_border
            ? y - tooltip_size.height + "px"
            : y + "px";
        this._tooltip
            .style("left", left)
            .style("right", "auto")
            .style("bottom", "auto")
            .style("top", top)
            .style("pointer-events", "none")
            .style("opacity", 1);
    }

    add_support(node: SVGGElement) {
        const element = select(node);
        element
            .on("mouseover", event => this._mouseover(event))
            .on("mouseleave", event => this._mouseleave(event))
            .on("mousemove", event => this._mousemove(event));
    }

    activate() {
        select(this._tooltip.node()!.closest("div.dashlet")).style(
            "z-index",
            "99",
        );
        this._tooltip.style("display", null);
    }

    deactivate() {
        select(this._tooltip.node()!.closest("div.dashlet")).style(
            "z-index",
            "",
        );
        this._tooltip.style("display", "none");
    }

    active() {
        return this._tooltip.style("display") != "none";
    }

    _mouseover(event: MouseEvent) {
        const node_data = select(event.target as HTMLDivElement).datum();
        // @ts-ignore
        if (node_data == undefined || node_data.tooltip == undefined) return;
        this.activate();
    }

    _mousemove(event: MouseEvent) {
        const node_data = select(event.target as HTMLDivElement).datum();
        // @ts-ignore
        if (node_data == undefined || node_data.tooltip == undefined) return;
        // @ts-ignore
        this._tooltip.html(node_data.tooltip);
        this.update_position(event);
    }

    _mouseleave(_event: MouseEvent) {
        this.deactivate();
    }
}
