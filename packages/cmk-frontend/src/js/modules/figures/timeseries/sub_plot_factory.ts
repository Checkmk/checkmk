/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {SubPlot} from "./sub_plot";

export type SubplotConstructor = new (plotDefinition: any) => SubPlot;

export class SubPlotFactory {
    _plot_types: Record<string, SubplotConstructor>;

    constructor() {
        this._plot_types = {};
    }

    get_plot(plot_type: string) {
        return this._plot_types[plot_type];
    }

    register(subplot: SubplotConstructor) {
        this._plot_types[subplot.prototype.ident()] = subplot;
    }
}
