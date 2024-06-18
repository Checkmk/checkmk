/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import * as d3 from "d3";

import {
    NtopTalkerData,
    NtopTalkerDataPlotDefinition,
    TableFigureData,
} from "@/modules/figures/cmk_table";
import * as cmk_table from "@/modules/figures/cmk_table";

import * as ntop_utils from "./ntop_utils";

export class TopTalkersDashlet extends cmk_table.TableFigure {
    _default_params;
    //the following parameters are directly set after initializing
    //the class in cmk/gui/cee/plugins/dashboard/ntop_dashlets.py:215
    _ifid!: string;
    _vlanid!: string;
    constructor(tabs_bar: string) {
        super(tabs_bar);
        this._post_url = "ajax_ntop_top_talkers.py";
        this._default_params = {};
        this.scheduler.enable();
        this.scheduler.set_update_interval(60);
    }

    override initialize() {
        cmk_table.TableFigure.prototype.initialize.call(this, false);
        this._div_selection.classed(ntop_utils.ifid_dep, true);
    }

    set_ids(ifid: string, vlanid = "0") {
        this._ifid = ifid;
        this._vlanid = vlanid;
        this._post_body = new URLSearchParams(
            Object.assign({}, this._default_params, {
                ifid: this._ifid,
                vlanid: this._vlanid,
            })
        ).toString();
        this.scheduler.force_update();
    }

    override update_data(data: TableFigureData<NtopTalkerData>) {
        // Add some nice colors to the plot definitions
        const definitions_to_update: NtopTalkerDataPlotDefinition[][] = [];

        data["rows"].forEach(d =>
            d["cells"].forEach(c =>
                c["figure_config"]
                    ? definitions_to_update.push(
                          c["figure_config"]["plot_definitions"]
                      )
                    : null
            )
        );
        definitions_to_update.forEach(entry => {
            entry.forEach((definition, idx) => {
                definition.color = d3.schemePaired[idx];
            });
        });

        cmk_table.TableFigure.prototype.update_data.call(this, data);
    }
}
