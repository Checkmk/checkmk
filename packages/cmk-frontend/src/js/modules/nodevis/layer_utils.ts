/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {
    d3SelectionDiv,
    d3SelectionG,
    NodevisNode,
    NodevisWorld,
} from "./type_defs";
import type {TypeWithName} from "./utils";
import {AbstractClassRegistry} from "./utils";

export interface LayerSelections {
    div: d3SelectionDiv;
    svg: d3SelectionG;
}

export interface OverlayElement {
    node: NodevisNode;
    type: string;
    image: string;
    call: d3.DragBehavior<any, any, any>;
    onclick?: () => void;
}

export class AbstractLayer extends Object implements TypeWithName {
    enabled = false;
    _world: NodevisWorld;
    _div_selection: d3SelectionDiv;
    _svg_selection: d3SelectionG;

    constructor(world: NodevisWorld, selections: LayerSelections) {
        super();
        this._world = world;
        this._div_selection = selections.div;
        this._svg_selection = selections.svg;
    }

    is_dynamic_instance_template() {
        return false;
    }

    class_name() {
        return "abstract_layer";
    }

    id(): string {
        return "base_layer";
    }

    z_index(): number {
        return 10;
    }

    name(): string {
        return "base_layer_name";
    }

    supports_datasource(_datasource_name: string) {
        return true;
    }

    enable(): void {
        this.enabled = true;
        // Setup components
        this.setup();
        // Scale to size
        this.size_changed();
        // Adjust zoom
        this.zoomed();
        // Update data references
        this.update_data();
        // Update gui
        this.update_gui();
        this.enable_hook();
    }

    disable(): void {
        this.enabled = false;

        this.disable_hook();
        this._svg_selection.selectAll("*").remove();
        this._div_selection.selectAll("*").remove();
    }

    enable_hook(): void {
        return;
    }
    disable_hook(): void {
        return;
    }

    setup(): void {
        return;
    }

    // Called when the viewport size has changed
    size_changed(): void {
        return;
    }

    zoomed(): void {
        return;
    }

    set_enabled(is_enabled: boolean): void {
        this.enabled = is_enabled;
        if (this.enabled) this._world.viewport.enable_layer(this.id());
        else this._world.viewport.disable_layer(this.id());
    }

    is_enabled(): boolean {
        return this.enabled;
    }

    update_data(): void {
        return;
    }

    update_gui(_force_gui_update = false): void {
        return;
    }

    render_context_menu(_event: MouseEvent, _node_id: string | null): void {
        return;
    }

    hide_context_menu(_event: MouseEvent): void {
        return;
    }

    get_div_selection(): d3SelectionDiv {
        return this._div_selection;
    }

    get_svg_selection(): d3SelectionG {
        return this._svg_selection;
    }
}

// base class for layered viewport overlays
export class ToggleableLayer extends AbstractLayer {}

export class DynamicToggleableLayer extends ToggleableLayer {}

export class FixLayer extends AbstractLayer {}
class LayerClassRegistry extends AbstractClassRegistry<AbstractLayer> {}

export const layer_class_registry = new LayerClassRegistry();

export type AbstractNodeVisConstructor<Type extends TypeWithName> = new (
    a?: any,
    b?: any,
    c?: any,
    d?: any,
) => Type;
