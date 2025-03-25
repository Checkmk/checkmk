/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {TextFigureData} from "@/modules/figures/cmk_figures";
import {TextFigure} from "@/modules/figures/cmk_figures";
import {
    metric_value_component,
    metric_value_component_options_big_centered_text,
} from "@/modules/figures/cmk_figures_utils";

interface StateSummaryElement {
    in_state: StateSummaryPart;
    total: StateSummaryPart;
}

interface StateSummaryPart {
    count: number;
    url: string;
}

interface HostStateSummaryData extends TextFigureData<StateSummaryElement> {
    data: StateSummaryElement;
}

export class HostStateSummary extends TextFigure<HostStateSummaryData> {
    getEmptyData() {
        return {
            title: "",
            title_url: "",
            data: {
                in_state: {
                    count: 0,
                    url: "",
                },
                total: {
                    count: 0,
                    url: "string",
                },
            },
            plot_definitions: [],
        };
    }
    override ident() {
        return "host_state_summary";
    }

    override render() {
        const summary_data = this._data.data;
        if (!summary_data.in_state || !summary_data.total) return;
        this.render_title(this._data.title, this._data.title_url!);

        const text =
            summary_data.in_state.count.toString() +
            "/" +
            summary_data.total.count.toString();
        const value_font_size = Math.min(
            this.plot_size.width / text.length,
            (this.plot_size.height * 2) / 3,
        );
        metric_value_component(this.plot, {
            value: {
                value: text,
                url: summary_data.in_state.url,
            },
            ...metric_value_component_options_big_centered_text(
                this.plot_size,
                {
                    font_size: value_font_size,
                },
            ),
        });
    }
}

export class ServiceStateSummary extends HostStateSummary {
    override ident() {
        return "service_state_summary";
    }
}
