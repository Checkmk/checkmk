/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {HierarchyNode, Selection} from "d3";
import {hierarchy as d3hierarchy} from "d3";

import type {DatasourceManager} from "./datasources";
import type {ForceOptions} from "./force_utils";
import type {
    AbstractLayoutStyle,
    SerializedNodevisLayout,
} from "./layout_utils";
import type {Viewport} from "./viewport";

export type d3Selection = Selection<any, unknown, any, unknown>;

export type d3SelectionDiv = Selection<HTMLDivElement, null, any, unknown>;
export type d3SelectionSvg = Selection<SVGSVGElement, null, any, any>;
export type d3SelectionG = Selection<SVGGElement, null, any, any>;

export type DatasourceType = "bi_aggregations" | "topology";
export class NodevisWorld {
    root_div: d3SelectionDiv;
    viewport: Viewport;
    datasource_manager: DatasourceManager;
    datasource: DatasourceType = "bi_aggregations";

    update_data: () => void;
    update_browser_url: () => void;
    save_layout: () => void;
    delete_layout: () => void;

    constructor(
        root_div: d3SelectionDiv,
        viewport: Viewport,
        datasource: DatasourceType,
        datasource_manager: DatasourceManager,
        callback_update_data: () => void,
        callback_update_browser_url: () => void,
        callback_save_layout: () => void,
        callback_delete_layout: () => void,
    ) {
        this.root_div = root_div;
        this.viewport = viewport;
        this.datasource_manager = datasource_manager;
        this.update_data = callback_update_data;
        this.update_browser_url = callback_update_browser_url;
        this.save_layout = callback_save_layout;
        this.delete_layout = callback_delete_layout;
        this.datasource = datasource;
    }
}

export interface Rectangle {
    width: number;
    height: number;
}

export interface Coords {
    x: number;
    y: number;
}

export class InputRangeOptions {
    id: string;
    title: string;
    step: number;
    min: number;
    max: number;
    default_value: number;
    constructor(
        id: string,
        title: string,
        step: number,
        min: number,
        max: number,
        default_value: number,
    ) {
        this.id = id;
        this.title = title;
        this.step = step;
        this.min = min;
        this.max = max;
        this.default_value = default_value;
    }
}

export type XYCoords = [number, number];
export interface RectangleWithCoords extends Rectangle, Coords {}

export interface BoundingRect {
    x_min: number;
    x_max: number;
    y_min: number;
    y_max: number;
    width: number;
    height: number;
}

export class SearchResultEntry {
    name = "";
    state = 0;
}

export class SearchResults {
    type = "node";
    entries: SearchResultEntry[] = [];
}

export interface DatasourceCallback {
    (data: any): void;
}

export class OverlayConfig {
    active: boolean;
    constructor(active: boolean) {
        this.active = active;
    }
}

export class ComputationOptions {
    merge_nodes: boolean;
    show_services: "all" | "none" | "only_problems";
    hierarchy: string;
    enforce_hierarchy_update: boolean;
    constructor(
        merge_nodes = false,
        show_services: "all" | "none" | "only_problems" = "all",
        hierarchy: "flat" | "full" = "full",
        enforce_hierarchy_update = false,
    ) {
        this.merge_nodes = merge_nodes;
        this.show_services = show_services;
        this.hierarchy = hierarchy;
        this.enforce_hierarchy_update = enforce_hierarchy_update;
    }
}

export class OverlaysConfig {
    available_layers: string[];
    overlays: Record<string, OverlayConfig>;
    computation_options: ComputationOptions;
    constructor(
        available_layers: string[] = [],
        overlays: Record<string, OverlayConfig> = {},
        computation_options: ComputationOptions = new ComputationOptions(),
    ) {
        this.available_layers = available_layers;
        this.overlays = overlays;
        this.computation_options = computation_options;
    }

    static create_from_json(config_as_json: Record<string, any>) {
        const fake_object = config_as_json as OverlaysConfig;
        const overlays: Record<string, OverlayConfig> = {};
        Object.entries(fake_object.overlays).forEach(([key, value]) => {
            overlays[key] = new OverlayConfig(value.active);
        });
        const options = fake_object.computation_options;
        const computation_options = new ComputationOptions(
            options.merge_nodes,
            options.show_services,
            options.hierarchy as "flat" | "full",
            options.enforce_hierarchy_update,
        );
        return new OverlaysConfig(
            fake_object.available_layers,
            overlays,
            computation_options,
        );
    }
}

export interface TopologyFrontendConfig {
    overlays_config: OverlaysConfig;
    growth_root_nodes: string[];
    growth_forbidden_nodes: string[];
    growth_continue_nodes: string[];
    custom_node_settings: {[name: string]: any};
    datasource_configuration: {
        available_datasources: string[];
        reference: string;
        compare_to: string;
    };
}

export interface SerializedNodeConfig {
    hierarchy: NodeData;
    links: SerializedNodevisLink[];
}
export interface BackendResponse {
    headline: string;
    errors: string;
    node_config: SerializedNodeConfig;
    layout: SerializedNodevisLayout;
}

export interface TopologyBackendResponse extends BackendResponse {
    frontend_configuration: TopologyFrontendConfig;
}

export interface GrowthSettings {
    // Growth stuff for topology
    growth_root: boolean;
    growth_forbidden: boolean;
    growth_continue: boolean;
    indicator_growth_possible: boolean;
    indicator_growth_root: boolean;
}

export interface NodeData {
    children?: NodeData[];
    id: string;
    node_type: string;
    name: string;
    node_positioning: Record<string, any>;
    user_interactions: Record<string, any>;
    invisible?: boolean;
    icon_image: string;
    acknowledged: boolean;
    in_downtime: boolean;
    show_text: boolean;
    state: 0 | 1 | 2 | 3;
    target_coords: Coords;
    box_leaf_nodes?: boolean;
    custom_node_settings?: Record<string, any>;

    use_style: AbstractLayoutStyle | null;

    type_specific: Record<string, any>;
    // TODO: move topo stuff
    growth_settings: GrowthSettings;

    // Positioning
    current_positioning: {
        type: string;
        free?: boolean;
        text_positioning?: (x?: any) => any; // this should be selection but couldn't figure out a way to generically type it,
        hide_node_link?: boolean;
    };

    explicit_force_options: ForceOptions | null;

    transition_info: {
        type?: string;
        use_transition?: boolean;
    };

    // TODO: remove host service specific
    hostname: string;
    service: string;

    // TODO: remove BI specific
    aggr_path_id: [string, number][];
    aggr_path_name: [string, number][];
    rule_id: {
        pack: string;
        rule: string;
        aggregation_function_description: string;
    };
    rule_layout_style?: {[name: string]: any};
}

export interface CoreInfo {
    hostname: string;
    service?: string;
    state?: number;
    acknowledged?: boolean;
    in_downtime?: boolean;
}

export interface LineConfig {
    thickness?: number;
    color?: string;
    tooltip?: string;
    css_styles?: Record<string, any>;
}

export type QuickinfoEntry = {
    name: string;
    value: string;
    css_styles?: Record<string, any>;
};

export type Quickinfo = QuickinfoEntry[];

export interface Tooltip {
    html?: string;
    quickinfo?: Quickinfo;
}

export interface LinkConfig {
    type: "default";
    line_config?: LineConfig;
    tooltip?: Tooltip;
    topology_classes?: [string, boolean][];
}

export interface SerializedNodevisLink {
    source: string;
    target: string;
    config: LinkConfig;
}

export interface NodevisLink {
    source: NodevisNode;
    target: NodevisNode;
    config: LinkConfig;
}

export interface ContextMenuElement {
    text?: string;
    href?: string;
    img?: string;
    tick?: boolean;
    dom?: HTMLDivElement;
    on?: (event: Event, data: any) => void;
    data?: any;
    element_source?: string;
    children?: ContextMenuElement[];
}

export interface NodeVisHierarchyNode<Datum> extends HierarchyNode<Datum> {
    _children?: this[] | undefined | null;
    x: number; // can also be undefined in original type definition
    y: number; // can also be undefined in original type definition
    fx: number | null;
    fy: number | null;
    force?: number;
    use_transition?: boolean;
    children_backup?: this[];
}

// TODO: add class
export interface LayoutSettings {
    origin_info: string;
    origin_type: "explicit" | "default_template";
    default_id: string;
    config: SerializedNodevisLayout;
}

export class NodeConfig {
    hierarchy: NodeVisHierarchyNode<NodeData>;
    link_info: NodevisLink[];
    nodes_by_id: Record<string, NodeVisHierarchyNode<NodeData>>;
    constructor(serialized_node_config: SerializedNodeConfig) {
        this.hierarchy = this._create_hierarchy(serialized_node_config);
        this.nodes_by_id = this._create_nodes_by_id_lookup(this.hierarchy);
        this.link_info = this._create_link_references(
            serialized_node_config.links,
        );
    }

    create_empty_config() {
        const empty_chunk = {
            hierarchy: {invisible: true},
            links: [],
        } as unknown as SerializedNodeConfig;
        return new NodeConfig(empty_chunk);
    }

    _create_hierarchy(
        serialized_node_config: SerializedNodeConfig,
    ): NodeVisHierarchyNode<NodeData> {
        const hierarchy = d3hierarchy<NodeData>(
            serialized_node_config.hierarchy,
        ) as NodeVisHierarchyNode<NodeData>;
        // Initialize default info of each node
        hierarchy.descendants().forEach(node => {
            node._children = node.children;
            node.data.node_positioning = {};
            node.data.transition_info = {};
            // User interactions, e.g. collapsing node, root cause analysis
            node.data.user_interactions = {};
        });
        return hierarchy;
    }

    _create_nodes_by_id_lookup(hierarchy: NodeVisHierarchyNode<NodeData>) {
        const nodes_by_id: Record<string, NodeVisHierarchyNode<NodeData>> = {};
        hierarchy.descendants().forEach(node => {
            nodes_by_id[node.data.id] = node;
        });
        return nodes_by_id;
    }

    _create_link_references(
        link_info: SerializedNodevisLink[] | null,
    ): NodevisLink[] {
        const links: NodevisLink[] = [];
        if (link_info != null) {
            // The chunk specified its own links
            link_info.forEach(link => {
                // Reference by id:string
                links.push({
                    source: this.nodes_by_id[link.source] as NodevisNode,
                    target: this.nodes_by_id[link.target] as NodevisNode,
                    config: link.config,
                });
            });
            return links;
        }

        // Create links out of the hierarchy layout
        // A simple tree with one root node, branches and leafs
        this.hierarchy.descendants().forEach(node => {
            if (!node.parent || node.data.invisible) return;
            links.push({
                source: node as NodevisNode,
                target: node.parent as NodevisNode,
                config: {type: "default"},
            });
        });
        return links;
    }
}

export type NodevisNode = NodeVisHierarchyNode<NodeData>;
