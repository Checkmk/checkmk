// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

export class ToolbarPluginBase extends Object {
    static id() {}

    constructor(description, main_instance) {
        super();
        this.main_instance = main_instance;
        this.description = description;
        this.active = false;
        this.content_selection = null;
    }

    setup_selections(content_selection) {
        this.content_selection = content_selection;
    }

    has_toggle_button() {
        return true;
    }

    render_togglebutton() {}

    description() {
        return this.description;
    }

    enable() {
        this.active = true;
        this.enable_actions();
        this.render_content();
    }

    enable_actions() {}

    render_content() {}

    disable() {
        this.active = false;
        this.disable_actions();
        this.remove_content();
    }

    disable_actions() {}

    remove_content() {
        if (this.content_selection) this.content_selection.selectAll("*").remove();
    }
}
