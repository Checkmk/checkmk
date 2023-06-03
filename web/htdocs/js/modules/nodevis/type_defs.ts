import * as d3 from "d3";
import {HierarchyNode} from "d3";
import {DatasourceManager} from "nodevis/datasources";
import {ForceOptions, ForceSimulation} from "nodevis/force_simulation";
import {InfoBox} from "nodevis/infobox";
import {LayeredNodesLayer} from "nodevis/layers";
import {LayoutManagerLayer} from "nodevis/layout";
import {
    AbstractLayoutStyle,
    LineConfig,
    NodeVisualizationLayout,
    StyleConfig,
} from "nodevis/layout_utils";
import {NodeVisualization} from "nodevis/main";
import {Toolbar} from "nodevis/toolbar";
import {LayeredViewport} from "nodevis/viewport";

export type d3SelectionDiv = d3.Selection<
    HTMLDivElement,
    unknown,
    any,
    unknown
>;
export type d3SelectionSvg = d3.Selection<SVGSVGElement, unknown, any, any>;
export type d3SelectionG = d3.Selection<SVGGElement, unknown, any, any>;
export type d3SelectionSvgText = d3.Selection<
    SVGTextElement,
    unknown,
    any,
    any
>;
export type d3NodeSelection = d3.Selection<
    SVGGElement,
    NodevisNode,
    SVGGElement,
    any
>;

export class NodevisWorld {
    root_div: d3SelectionDiv;
    datasource_manager: DatasourceManager;
    toolbar: Toolbar;
    viewport: LayeredViewport;
    infobox: InfoBox;
    layout_manager: LayoutManagerLayer;
    force_simulation: ForceSimulation;
    current_datasource: "bi_aggregations" | "topology" = "bi_aggregations";
    nodes_layer: LayeredNodesLayer;
    main_instance: NodeVisualization;

    update_data: () => void;
    update_browser_url: () => void;
    save_layout: () => void;
    delete_layout: () => void;

    constructor(
        root_div: d3SelectionDiv,
        datasource_manager: DatasourceManager,
        toolbar: Toolbar,
        viewport: LayeredViewport,
        infobox: InfoBox,
        force_simulation: ForceSimulation,
        callback_update_data: () => void,
        callback_update_browser_url: () => void,
        callback_save_layout: () => void,
        callback_delete_layout: () => void,
        main_instance: NodeVisualization
    ) {
        // TODO: This code is never called :) o.O
        this.root_div = root_div;
        this.datasource_manager = datasource_manager;
        this.viewport = viewport;
        this.infobox = infobox;
        this.toolbar = toolbar;
        this.force_simulation = force_simulation;
        this.layout_manager = this.viewport._world.layout_manager;
        this.nodes_layer = this.viewport.get_layer(
            "nodes"
        ) as LayeredNodesLayer;
        this.main_instance = main_instance;
        this.update_data = callback_update_data;
        this.update_browser_url = callback_update_browser_url;
        this.save_layout = callback_save_layout;
        this.delete_layout = callback_delete_layout;
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
    datasource = "";
    type = "node";
    entries: SearchResultEntry[] = [];
}

export interface DatasourceCallback {
    (data: any): void;
}

export interface BackendChunkResponse {
    chunks: SerializedNodeChunk[];
    use_layout?: {[name: string]: any};
}

export interface SerializedNodeChunk {
    type: string;
    layout: {
        config: {
            line_config: LineConfig;
        };
    };
    marked_obsolete: boolean;
    hierarchy: NodeData;
    links: SerializedNodevisLink[];
}

export interface NodeData {
    children?: NodeData[];
    id: string;
    node_type: string;
    name: string;
    node_positioning: {[name: string]: any};
    chunk: NodeChunk;
    user_interactions: {[name: string]: any};
    invisible?: boolean;
    icon_image: string;
    acknowledged: boolean;
    in_downtime: boolean;
    show_text: boolean;
    state: number;
    target_coords: Coords;
    has_no_parents: boolean;
    box_leaf_nodes?: boolean;
    custom_node_settings?: {[name: string]: any};

    use_style: AbstractLayoutStyle | null;

    // TODO: most important, remove this selection. this reference is too volatile
    selection: d3SelectionG;

    // TODO: move topo stuff
    // Growth stuff for topology
    growth_root: boolean;
    growth_forbidden: boolean;
    growth_possible: boolean;
    growth_continue: boolean;

    // Positioning
    current_positioning: {
        type: string;
        free?: boolean;
        text_positioning?: (x) => any;
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

    //    // TODO: remove BI specific
    aggr_path_id: [string, number][];
    aggr_path_name: [string, number][];
    rule_id: {
        pack: string;
        rule: string;
        aggregation_function_description: string;
    };
    rule_layout_style?: {[name: string]: any};
}

export interface LinkConfig {
    type: "default";
    width?: number;
    color?: string;
    css?: string;
    link_info?: string;
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
    text: string;
    href?: string;
    img?: string;
    on?: (event?) => void;
}

declare module "d3" {
    // @typescript-eslint/no-unused-vars
    export interface HierarchyNode<Datum> {
        data: Datum;
        _children?: this[] | null;
        x: number;
        y: number;
        fx: number | null;
        fy: number | null;
    }
}

// TODO: add class
interface LayoutSettings {
    origin_info: string;
    origin_type: "explicit" | "default_template";
    default_id: string;
    config: {
        line_config: LineConfig;
        style_configs: StyleConfig[];
        delayed_style_configs?: StyleConfig[];
        force_options?: ForceOptions;
        ignore_rule_styles?: boolean;
    };
}

// TODO: Change to interface, create instance elsewhere
export class NodeChunk {
    id: string;
    type: string;
    coords: {x: number; y: number; width: number; height: number};
    marked_obsolete = false;
    tree: NodevisNode;
    links: NodevisLink[];

    nodes: NodevisNode[];
    nodes_by_id: {[name: string]: NodevisNode};

    // TODO: remove someday
    layout_instance: NodeVisualizationLayout | null;
    layout_settings: LayoutSettings;
    aggr_type: "single" | "multi" = "multi";
    template_id: string | null = null;

    constructor(
        type: string,
        hierarchy: NodevisNode,
        link_info: SerializedNodevisLink[],
        layout_settings: LayoutSettings
    ) {
        this.type = type;
        this.tree = hierarchy;
        this.coords = {x: 0, y: 0, width: 0, height: 0};
        this.nodes = this.tree.descendants();
        this.nodes_by_id = {};
        this.nodes.forEach(node => {
            this.nodes_by_id[node.data.id] = node;
            node.data.chunk = this;
        });

        this.id = this.nodes[0].data.id;
        this.layout_settings = layout_settings;
        this.layout_instance = null;

        this.links = this._resolve_link_references(link_info);
    }

    _resolve_link_references(
        link_info: SerializedNodevisLink[]
    ): NodevisLink[] {
        const links: NodevisLink[] = [];
        if (link_info) {
            // The chunk specified its own links
            link_info.forEach(link => {
                // Reference by id:string
                links.push({
                    source: this.nodes_by_id[link.source],
                    target: this.nodes_by_id[link.target],
                    config: link.config,
                });
            });
            return links;
        }

        // Create links out of the hierarchy layout
        // A simple tree with one root node, branches and leafs
        this.nodes.forEach(node => {
            if (!node.parent || node.data.invisible) return;
            links.push({
                source: node,
                target: node.parent,
                config: {type: "default"},
            });
        });
        return links;
    }
}

export type NodevisNode = HierarchyNode<NodeData>;
