/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {
    d3SelectionDiv,
    d3SelectionG,
    NodevisNode,
    NodevisWorld,
} from "nodevis/type_defs";
import {AbstractClassRegistry, TypeWithName} from "nodevis/utils";

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

type OverlayConfigMandatory = Record<string, number | string | boolean>;

export interface OverlayConfig extends OverlayConfigMandatory {
    active: boolean;
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

        // TODO: sort index for div and svg layers
        // d3js can rearrange dom with sorting
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

    enable(): void {
        this.enabled = true;

        // Setup components
        this.setup();
        // Scale to size
        this.size_changed();

        // Without data simply return
        if (this._world.viewport.get_all_nodes().length == 0) return;

        // Adjust zoom
        this.zoomed();
        // Update data references
        this.update_data();
        // Update gui
        this.update_gui();
    }

    disable(): void {
        this.enabled = false;

        this.disable_hook();
        this._svg_selection.selectAll("*").remove();
        this._div_selection.selectAll("*").remove();
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
export class ToggleableLayer extends AbstractLayer {
    overlay_active = false;
}

export class FixLayer extends AbstractLayer {}
class LayerClassRegistry extends AbstractClassRegistry<AbstractLayer> {}

export const layer_class_registry = new LayerClassRegistry();

export type AbstractNodeVisConstructor<Type extends TypeWithName> = new (
    a?: any,
    b?: any,
    c?: any,
    d?: any
) => Type;
