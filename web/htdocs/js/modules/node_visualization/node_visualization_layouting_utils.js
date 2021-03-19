// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as node_visualization_layout from "node_visualization_layout";

export class LayoutStyleFactory {
    constructor(layout_manager) {
        this.layout_manager = layout_manager;
        this.style_templates = {};
        this.load_styles();
    }

    load_styles() {
        LayoutStyleFactory.style_classes.forEach(style => {
            this.style_templates[style.prototype.type()] = style;
        });
    }

    get_styles() {
        return this.style_templates;
    }

    get_style_class(style_config) {
        return this.style_templates[style_config.type];
    }

    // Creates a style instance with the given style_config
    instantiate_style(style_config, node, selection) {
        return new (this.get_style_class(style_config))(
            this.layout_manager,
            style_config,
            node,
            selection
        );
    }

    instantiate_style_name(style_name, node, selection) {
        return this.instantiate_style({type: style_name}, node, selection);
    }

    instantiate_style_class(style_class, node, selection) {
        return this.instantiate_style({type: style_class.prototype.type()}, node, selection);
    }
}

LayoutStyleFactory.style_classes = [];
