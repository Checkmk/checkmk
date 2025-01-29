/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {TextFigureData} from "@/modules/figures/cmk_figures";
import {TextFigure} from "@/modules/figures/cmk_figures";
import {clamp} from "@/modules/figures/cmk_figures_utils";

interface InventoryFigureDataData {
    unit: string;
    value: null | string | number;
    url: string;
}

interface InventoryFigureDataPlotDefinition {
    id: string;
    plot_type: string;
}

interface InventoryFigureData<D = any, P = any> extends TextFigureData<D, P> {
    data: D[];
}

export class InventoryFigure extends TextFigure<
    InventoryFigureData<
        InventoryFigureDataData,
        InventoryFigureDataPlotDefinition
    >
> {
    getEmptyData(): InventoryFigureData<
        InventoryFigureDataData,
        InventoryFigureDataPlotDefinition
    > {
        return {
            data: [],
            plot_definitions: [],
            title: "",
            title_url: "",
        };
    }

    override ident() {
        return "inventory";
    }

    override render() {
        const plot = this._data.plot_definitions[0];
        if (!plot) {
            // rendering before the first ajax call
            return;
        }

        const inventory_data = this._data.data[0];
        this.render_title(this._data.title, this._data.title_url!);

        const font_size = clamp(
            Math.min(this.plot_size.width / 5, (this.plot_size.height * 2) / 3),
            [12, 50],
        );

        const link = this.plot
            .selectAll("a.inventory")
            .data([inventory_data])
            .join("a")
            .classed("inventory", true)
            .attr("xlink:href", d => d.url || null);
        const text = link
            .selectAll("foreignObject")
            .data(d => [d])
            .join("foreignObject")
            .attr("width", "100%")
            .attr("height", "100%")
            .selectAll("div")
            .data(d => [d])
            .join("xhtml:div")
            .selectAll("div")
            .data(d => [d])
            .join("xhtml:div")
            .text(d => d.value)
            .style("font-size", font_size + "px");

        if (inventory_data.unit !== undefined) {
            text.selectAll("span")
                .data(d => [d])
                .join("span")
                .style("font-size", font_size / 2 + "px")
                .style("font-weight", "lighter")
                .text(d => d.unit);
        }
    }
}
