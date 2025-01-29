/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {ForceSimulation} from "./force_simulation";
import type {StyleOptionSpecRange, StyleOptionValues} from "./layout_utils";

export type ForceOptions = {
    charge: number;
    center: number;
    collide: number;
    link_distance: number;
    link_strength: number;
    [name: string]: number;
};

export class ForceConfig {
    _force_simulation: ForceSimulation;
    options: ForceOptions;
    description = "Force configuration";

    constructor(
        force_simulation: ForceSimulation,
        options: ForceOptions | null = null,
    ) {
        this._force_simulation = force_simulation;
        if (options == null) options = this.get_default_options();
        this.options = options;
    }

    get_default_options(): ForceOptions {
        const default_options: ForceOptions = {} as ForceOptions;
        this.get_style_options().forEach(option => {
            default_options[option.id] = option.values.default;
        });
        return default_options;
    }

    changed_options(new_options: StyleOptionValues) {
        this.options = new_options as ForceOptions;
        this._force_simulation.setup_forces();
        this._force_simulation.restart_with_alpha(0.5);
    }

    get_style_options(): StyleOptionSpecRange[] {
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
                text: "Repulsion force",
            },
            {
                id: "link_distance",
                values: {default: 30, min: -10, max: 500, step: 1},
                option_type: "range",
                text: "Link distance",
            },
            {
                id: "link_strength",
                values: {default: 0.3, min: 0, max: 4, step: 0.01},
                option_type: "range",
                text: "Link strength",
            },
            {
                id: "collide",
                values: {default: 15, min: 0, max: 150, step: 1},
                option_type: "range",
                text: "Collision box",
            },
        ];
    }
}

export type SimulationForce =
    | "charge"
    | "collide"
    | "center"
    | "link_distance"
    | "link_strength";
