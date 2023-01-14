import * as d3 from "d3";
import {
    ContextMenuElement,
    NodevisNode,
    NodevisWorld,
    SimulationForce,
} from "nodevis/type_defs";
import {
    AbstractGUINode,
    BasicQuickinfo,
    node_type_class_registry,
} from "nodevis/node_utils";
import {TypeWithName} from "nodevis/utils";

export class TopologyNode extends AbstractGUINode {
    static class_name = "topology";

    constructor(world: NodevisWorld, node) {
        super(world, node);
        this.radius = 9;
        this._provides_external_quickinfo_data = true;
    }

    static id() {
        return "topology";
    }

    render_object() {
        AbstractGUINode.prototype.render_object.call(this);

        if (this.node.data.has_no_parents)
            this.selection().select("circle").classed("has_no_parents", true);

        this.selection().on("dblclick", () => this._toggle_growth_continue());
    }

    update_position() {
        AbstractGUINode.prototype.update_position.call(this);

        // Growth root
        const growth_root_selection = this.selection()
            .selectAll("circle.growth_root")
            .data([this.node]);
        if (this.node.data.growth_root) {
            growth_root_selection
                .enter()
                .append("circle")
                .classed("growth_root", true)
                .attr("r", this.radius + 4)
                .attr("fill", "none");
        } else growth_root_selection.remove();

        // Growth possible
        const growth_possible_selection = this.selection()
            .selectAll("image.growth_possible")
            .data([this.node]);
        if (this.node.data.growth_possible) {
            growth_possible_selection
                .enter()
                .append("svg:image")
                .classed("growth_possible", true)
                .attr("xlink:href", "themes/facelift/images/icon_hierarchy.svg")
                .attr("width", 16)
                .attr("height", 16)
                .attr("x", -8)
                .attr("y", 0);
        } else growth_possible_selection.remove();

        // Growth forbidden
        const growth_forbidden_selection = this.selection()
            .selectAll("image.growth_forbidden")
            .data([this.node]);
        if (this.node.data.growth_forbidden) {
            growth_forbidden_selection
                .enter()
                .append("svg:image")
                .classed("growth_forbidden", true)
                .attr("xlink:href", "themes/facelift/images/icon_no_entry.svg")
                .attr("width", 16)
                .attr("height", 16)
                .attr("x", -28)
                .attr("y", 0);
        } else growth_forbidden_selection.remove();
    }

    _fetch_external_quickinfo() {
        this._quickinfo_fetch_in_progress = true;
        const view_url =
            "view.py?view_name=topology_hover_host&display_options=I&host=" +
            encodeURIComponent(this.node.data.hostname);
        d3.html(view_url, {credentials: "include"}).then(html =>
            this._got_quickinfo(html)
        );
    }

    get_context_menu_elements() {
        let elements =
            AbstractGUINode.prototype.get_context_menu_elements.call(this);
        elements = elements.concat(this._get_topology_menu_elements());
        return elements;
    }

    _get_topology_menu_elements() {
        // Toggle root node
        const elements: ContextMenuElement[] = [];
        let root_node_text = "Add root node";
        if (this.node.data.growth_root) root_node_text = "Remove root node";
        elements.push({
            text: root_node_text,
            on: () => this._toggle_root_node(),
        });

        // Use this node as exclusive root node
        elements.push({text: "Set root node", on: () => this._set_root_node()});

        // Forbid further growth
        let growth_forbidden_text = "Forbid further hops";
        if (this.node.data.growth_forbidden)
            growth_forbidden_text = "Allow further hops";
        elements.push({
            text: growth_forbidden_text,
            on: () => this._toggle_stop_growth(),
        });
        return elements;
    }

    _toggle_stop_growth() {
        this.node.data.growth_forbidden = !this.node.data.growth_forbidden;
        this._world.update_data();
    }

    _toggle_root_node() {
        this.node.data.growth_root = !this.node.data.growth_root;
        this._world.update_data();
    }

    _set_root_node() {
        this._world.viewport.get_all_nodes().forEach(node => {
            node.data.growth_root = false;
        });
        this.node.data.growth_root = true;
        this._world.update_data();
    }

    _toggle_growth_continue() {
        this.node.data.growth_continue = !this.node.data.growth_continue;
        this._world.update_data();
    }

    _get_node_type_specific_force(force_name: SimulationForce): number {
        switch (force_name) {
            case "charge_force":
                return this.node.data.force_options.force_node;
            case "collide":
                return this.node.data.force_options.collision_force_node;
            case "center":
                return this.node.data.force_options.center_force / 300;
            case "link_distance":
                return this.node.data.force_options.link_force_node;
            case "link_strength":
                return this.node.data.force_options.link_strength / 100;
            default:
                return 0;
        }
    }
}

export class TopologyCentralNode extends TopologyNode {
    static class_name = "topology_center";

    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 30;
        this._has_quickinfo = false;
    }

    static id() {
        return "topology_center";
    }

    render_object() {
        this.selection()
            .append("circle")
            .attr("r", this.radius)
            .classed("topology_center", true);
        this.selection()
            .append("svg:image")
            .attr("xlink:href", "themes/facelift/images/logo_cmk_small.png")
            .attr("x", -25)
            .attr("y", -25)
            .attr("width", 50)
            .attr("height", 50);
    }
}

export class TopologySiteNode extends TopologyNode {
    static class_name = "topology_site";

    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 16;
        this._has_quickinfo = false;
    }

    static id() {
        return "topology_site";
    }

    render_object() {
        this.selection()
            .append("circle")
            .attr("r", this.radius)
            .classed("topology_remote", true);
        this.selection()
            .append("svg:image")
            .attr("xlink:href", "themes/facelift/images/icon_sites.svg")
            .attr("x", -15)
            .attr("y", -15)
            .attr("width", 30)
            .attr("height", 30);
    }
}

export class BILeafNode extends AbstractGUINode implements TypeWithName {
    static class_name = "bi_leaf";

    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 9;
        this._provides_external_quickinfo_data = true;
    }

    static id() {
        return "bi_leaf";
    }

    _get_basic_quickinfo(): BasicQuickinfo[] {
        const quickinfo: BasicQuickinfo[] = [];
        quickinfo.push({name: "Host name", value: this.node.data.hostname});
        if (this.node.data.service)
            quickinfo.push({
                name: "Service description",
                value: this.node.data.service,
            });
        return quickinfo;
    }

    _fetch_external_quickinfo(): void {
        this._quickinfo_fetch_in_progress = true;
        let view_url;
        if (this.node.data.service)
            // TODO: add site to url
            view_url =
                "view.py?view_name=bi_map_hover_service&display_options=I&host=" +
                encodeURIComponent(this.node.data.hostname) +
                "&service=" +
                encodeURIComponent(this.node.data.service);
        else
            view_url =
                "view.py?view_name=bi_map_hover_host&display_options=I&host=" +
                encodeURIComponent(this.node.data.hostname);

        d3.html(view_url, {credentials: "include"}).then(html =>
            this._got_quickinfo(html)
        );
    }

    _get_details_url(): string {
        if (this.node.data.service && this.node.data.service != "") {
            return (
                "view.py?view_name=service" +
                "&host=" +
                encodeURIComponent(this.node.data.hostname) +
                "&service=" +
                encodeURIComponent(this.node.data.service)
            );
        } else {
            return (
                "view.py?view_name=host&host=" +
                encodeURIComponent(this.node.data.hostname)
            );
        }
    }

    _get_node_type_specific_force(force_name: SimulationForce): number {
        switch (force_name) {
            case "charge_force":
                return this.node.data.force_options.force_node;
            case "collide":
                return this.node.data.force_options.collision_force_node;
            case "center":
                return this.node.data.force_options.center_force / 300;
            case "link_distance":
                return this.node.data.force_options.link_force_node;
            case "link_strength":
                return this.node.data.force_options.link_strength / 100;
            default:
                return 0;
        }
    }
}

export class BIAggregatorNode extends AbstractGUINode {
    static class_name = "bi_aggregator";

    constructor(world: NodevisWorld, node: NodevisNode) {
        super(world, node);
        this.radius = 12;
        if (!this.node.parent)
            // the root node gets a bigger radius
            this.radius = 16;
    }

    static id() {
        return "bi_aggregator";
    }

    _get_basic_quickinfo(): BasicQuickinfo[] {
        const quickinfo: BasicQuickinfo[] = [];
        quickinfo.push({name: "Rule Title", value: this.node.data.name});
        quickinfo.push({
            name: "State",
            css_classes: ["state", "svcstate", "state" + this.node.data.state],
            value: this._state_to_text(this.node.data.state),
        });
        quickinfo.push({name: "Pack ID", value: this.node.data.rule_id.pack});
        quickinfo.push({name: "Rule ID", value: this.node.data.rule_id.rule});
        quickinfo.push({
            name: "Aggregation Function",
            value: this.node.data.rule_id.aggregation_function_description,
        });
        return quickinfo;
    }

    get_context_menu_elements(): ContextMenuElement[] {
        const elements: ContextMenuElement[] = [];

        // Local actions
        // TODO: provide aggregation ID (if available)
        //        if (!this.node.parent)
        //        // This is the aggregation root node
        //            elements.push({text: "Edit aggregation (Missing: You need to configure an ID for this aggregation)", href: "wato.py?mode=bi_edit_rule&id=" + this.node.data.rule_id.rule +
        //               "&pack=" + this.node.data.rule_id.pack,
        //               img: utils.get_theme() + "/images/icon_edit.png"})

        elements.push({
            text: "Edit rule",
            href:
                "wato.py?mode=bi_edit_rule&id=" +
                this.node.data.rule_id.rule +
                "&pack=" +
                this.node.data.rule_id.pack,
            img: "themes/facelift/images/icon_edit.svg",
        });

        if (this.node.children != this.node._children)
            elements.push({
                text: "Below this node, expand all nodes",
                on: event => {
                    event.stopPropagation();
                    this.expand_node_including_children(this.node);
                    this._world.viewport.recompute_node_chunk_descendants_and_links(
                        this.node.data.chunk
                    );
                },
                href: "",
                img: "themes/facelift/images/icon_expand.png",
            });
        else
            elements.push({
                text: "Collapse this node",
                on: event => {
                    event.stopPropagation();
                    this.collapse_node();
                },
                href: "",
                img: "themes/facelift/images/icon_collapse.png",
            });

        elements.push({
            text: "Expand all nodes",
            on: event => {
                event.stopPropagation();
                this.expand_node_including_children(this.node.data.chunk.tree);
                this._world.viewport.recompute_node_chunk_descendants_and_links(
                    this.node.data.chunk
                );
            },
            href: "",
            img: "themes/facelift/images/icon_expand.png",
        });

        elements.push({
            text: "Below this node, show only problems",
            on: event => {
                event.stopPropagation();
                this._filter_root_cause(this.node);
                this._world.viewport.recompute_node_chunk_descendants_and_links(
                    this.node.data.chunk
                );
            },
            img: "themes/facelift/images/icon_error.png",
        });
        return elements;
    }

    _get_node_type_specific_force(force_name: SimulationForce): number {
        switch (force_name) {
            case "charge_force":
                return this.node.data.force_options.force_aggregator;
            case "collide":
                return this.node.data.force_options.collision_force_aggregator;
            case "center":
                return this.node.data.force_options.center_force / 100;
            case "link_distance":
                return this.node.data.force_options.link_force_aggregator;
            case "link_strength":
                return this.node.data.force_options.link_strength / 100;
            default:
                return 0;
        }
    }
}

node_type_class_registry.register(TopologyNode);
node_type_class_registry.register(TopologySiteNode);
node_type_class_registry.register(TopologyCentralNode);
node_type_class_registry.register(BILeafNode);
node_type_class_registry.register(BIAggregatorNode);
