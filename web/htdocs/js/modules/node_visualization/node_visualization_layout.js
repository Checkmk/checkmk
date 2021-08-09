// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

export class NodeVisualizationLayout {
    constructor(viewport, id) {
        this.id = id;
        this.viewport = viewport;
        this.reference_size = {};
        this.style_configs = [];
        this.line_config = {style: "round"};
    }

    save_style(style_config) {
        this.style_configs.push(style_config);
    }

    clear_styles() {
        this.style_configs = [];
    }

    remove_style(style_instance) {
        let idx = this.style_configs.indexOf(style_instance.style_config);
        this.style_configs.splice(idx, 1);
    }

    serialize() {
        return {
            reference_size: this.reference_size,
            style_configs: this.style_configs,
            line_config: this.line_config,
        };
    }

    deserialize(data) {
        this.reference_size = data.reference_size;
        this.style_configs = data.style_configs;
        this.line_config = data.line_config;
    }
}
