// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import {d3SelectionDiv, NodevisWorld} from "nodevis/type_defs";

export class ToolbarPluginBase {
    _world: NodevisWorld;
    _div_selection: d3SelectionDiv | null = null;
    active: boolean;
    description = "";

    constructor(world: NodevisWorld, description: string) {
        this._world = world;
        this.description = description;
        this.active = true;
    }

    id(): string {
        return "toolbar_plugin_base";
    }

    instantiate(world: NodevisWorld): ToolbarPluginBase {
        throw "cannot instantiate ToolbarPluginBase class";
        return new ToolbarPluginBase(world, "ToolbarPluginBase description");
    }

    setup_selections(content_selection: d3SelectionDiv) {
        this._div_selection = content_selection;
    }

    has_toggle_button(): boolean {
        return true;
    }

    render_togglebutton(_selection: d3SelectionDiv): void {
        return;
    }

    enable(): void {
        this.active = true;
        this.enable_actions();
        this.render_content();
    }

    enable_actions(): void {
        return;
    }

    render_content(): void {
        return;
    }

    div_selection(): d3SelectionDiv {
        if (this._div_selection == null)
            throw "Toolbar plugin " + this.id() + " without _div_selection";
        return this._div_selection;
    }

    disable(): void {
        this.active = false;
        this.disable_actions();
        this.remove_content();
    }

    disable_actions(): void {
        return;
    }

    remove_content(): void {
        if (this._div_selection) this._div_selection.selectAll("*").remove();
    }

    sort_index(): number {
        return 10;
    }
}
