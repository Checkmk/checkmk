// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as d3 from "d3";
import * as node_visualization_viewport_utils from "node_visualization_viewport_utils";
import * as node_visualization_utils from "node_visualization_utils";
import * as node_visualization_layout_styles from "node_visualization_layout_styles";

export class LayeredDebugLayer extends node_visualization_viewport_utils.LayeredLayerBase {
    id() {
        return "debug_layer";
    }

    name() {
        return "Debug Layer";
    }

    setup() {
        this.overlay_active = false;
    }

    update_gui() {
        this.div_selection
            .selectAll("td#Simulation")
            .text(
                "Alpha: " +
                    node_visualization_layout_styles.force_simulation._simulation.alpha().toFixed(3)
            );
        if (this.overlay_active == this.viewport.layout_manager.edit_layout) return;

        if (this.viewport.layout_manager.edit_layout) this.enable_overlay();
        else this.disable_overlay();
    }

    _update_chunk_boundaries() {
        if (!this.viewport.layout_manager.edit_layout) {
            this.selection.selectAll("rect.boundary").remove();
            return;
        }

        let boundary_list = [];
        this.viewport.get_hierarchy_list().forEach(node_chunk => {
            let coords = this.viewport.translate_to_zoom(node_chunk.coords);
            coords.id = node_chunk.tree.data.id;
            boundary_list.push(coords);
        });

        let boundaries = this.selection.selectAll("rect.boundary").data(boundary_list, d => d.id);
        boundaries.exit().remove();
        boundaries = boundaries
            .enter()
            .append("rect")
            .classed("boundary", true)
            .attr("fill", "none")
            .attr("stroke", "black")
            .attr("stroke-width", 1)
            .merge(boundaries);

        boundaries
            .attr("x", d => d.x)
            .attr("y", d => d.y)
            .attr("width", d => d.width)
            .attr("height", d => d.height);
    }

    enable_overlay() {
        this.overlay_active = true;
        this.anchor_info = this.selection.append("g").attr("transform", "translate(-50,-50)");

        this.div_selection
            .append("input")
            .style("pointer-events", "all")
            .attr("id", "reset_pan_and_zoom")
            .attr("type", "button")
            .classed("button", true)
            .attr("value", "Reset panning and zoom")
            .on("click", () => this.reset_pan_and_zoom())
            .style("opacity", 0)
            .transition()
            .duration(node_visualization_utils.DefaultTransition.duration())
            .style("opacity", 1);

        this.viewport.selection.on("mousemove.translation_info", event => this.mousemove(event));
        let rows = this.div_selection
            .append("table")
            .attr("id", "translation_infobox")
            .selectAll("tr")
            .data(["Zoom", "Panning", "Mouse"]);
        //                    .selectAll("tr").data(["Zoom", "Panning", "Mouse", "Simulation"])
        let rows_enter = rows.enter().append("tr");
        rows_enter
            .append("td")
            .text(d => d)
            .classed("noselect", true);
        rows_enter
            .append("td")
            .attr("id", d => d)
            .classed("noselect", true);
        this.size_changed();
        this.zoomed();
    }

    disable_overlay() {
        this.overlay_active = false;
        this.selection
            .selectAll("*")
            .transition()
            .duration(node_visualization_utils.DefaultTransition.duration())
            .attr("opacity", 0)
            .remove();
        this.div_selection
            .selectAll("*")
            .transition()
            .duration(node_visualization_utils.DefaultTransition.duration())
            .style("opacity", 0)
            .remove();
        this.viewport.selection.on("mousemove.translation_info", null);
    }

    size_changed() {
        if (!this.overlay_active) return;
    }

    reset_pan_and_zoom() {
        this.viewport.svg_content_selection
            .transition()
            .duration(node_visualization_utils.DefaultTransition.duration())
            .call(this.viewport.main_zoom.transform, d3.zoomIdentity);
    }

    zoomed() {
        if (!this.overlay_active) return;
        this.anchor_info.attr("transform", this.viewport.last_zoom);
        this.div_selection.selectAll("td#Zoom").text(this.viewport.last_zoom.k.toFixed(2));
        this.div_selection
            .selectAll("td#Panning")
            .text(
                "X: " +
                    parseInt(this.viewport.last_zoom.x) +
                    " / Y:" +
                    parseInt(this.viewport.last_zoom.y)
            );
    }

    mousemove(event) {
        let coords = d3.pointer(event);
        this.div_selection
            .selectAll("td#Mouse")
            .text("X:" + parseInt(coords[0]) + " / Y:" + parseInt(coords[1]));
    }
}

export class LayeredIconOverlay extends node_visualization_viewport_utils.LayeredOverlayBase {
    id() {
        return "node_icon_overlay";
    }

    name() {
        return "Node icons";
    }

    update_gui() {
        let nodes = [];
        this.viewport.get_all_nodes().forEach(node => {
            if (!node.data.icon_image) return;
            nodes.push(node);
        });

        let icons = this.div_selection.selectAll("img").data(nodes, d => d.data.id);

        icons.exit().remove();
        icons = icons
            .enter()
            .append("img")
            .attr("src", d => "themes/facelift/images/icon_" + d.data.icon_image + ".svg")
            .classed("node_icon", true)
            .style("position", "absolute")
            .style("pointer-events", "none")
            .merge(icons);

        icons
            .style("left", d => {
                return this.viewport.translate_to_zoom({x: d.x, y: 0}).x - 24 + "px";
            })
            .style("top", d => {
                return this.viewport.translate_to_zoom({x: 0, y: d.y}).y - 24 + "px";
            });
    }
}

//#.
//#   .-Nodes Layer--------------------------------------------------------.
//#   |      _   _           _             _                               |
//#   |     | \ | | ___   __| | ___  ___  | |    __ _ _   _  ___ _ __      |
//#   |     |  \| |/ _ \ / _` |/ _ \/ __| | |   / _` | | | |/ _ \ '__|     |
//#   |     | |\  | (_) | (_| |  __/\__ \ | |__| (_| | |_| |  __/ |        |
//#   |     |_| \_|\___/ \__,_|\___||___/ |_____\__,_|\__, |\___|_|        |
//#   |                                               |___/                |
//#   +--------------------------------------------------------------------+

class TopologyCentralNode extends node_visualization_viewport_utils.TopologyNode {
    static id() {
        return "topology_center";
    }

    constructor(nodes_layer, node) {
        super(nodes_layer, node);
        this.radius = 30;
        this._has_quickinfo = false;
    }

    render_object() {
        this.selection.append("circle").attr("r", this.radius).classed("topology_center", true);
        this.selection
            .append("svg:image")
            .attr("xlink:href", "themes/facelift/images/logo_cmk_small.png")
            .attr("x", -25)
            .attr("y", -25)
            .attr("width", 50)
            .attr("height", 50);
    }
}

class TopologySiteNode extends node_visualization_viewport_utils.TopologyNode {
    static id() {
        return "topology_site";
    }

    constructor(nodes_layer, node) {
        super(nodes_layer, node);
        this.radius = 16;
        this._has_quickinfo = false;
    }

    render_object() {
        this.selection.append("circle").attr("r", this.radius).classed("topology_remote", true);
        this.selection
            .append("svg:image")
            .attr("xlink:href", "themes/facelift/images/icon_sites.svg")
            .attr("x", -15)
            .attr("y", -15)
            .attr("width", 30)
            .attr("height", 30);
    }
}

node_visualization_utils.node_type_class_registry.register(TopologySiteNode);
node_visualization_utils.node_type_class_registry.register(TopologyCentralNode);

class BILeafNode extends node_visualization_viewport_utils.AbstractGUINode {
    static id() {
        return "bi_leaf";
    }

    constructor(nodes_layer, node) {
        super(nodes_layer, node);
        this.radius = 9;
        this._provides_external_quickinfo_data = true;
    }

    _get_basic_quickinfo() {
        let quickinfo = [];
        quickinfo.push({name: "Host name", value: this.node.data.hostname});
        if ("service" in this.node.data)
            quickinfo.push({name: "Service description", value: this.node.data.service});
        return quickinfo;
    }

    _fetch_external_quickinfo() {
        this._quickinfo_fetch_in_progress = true;
        let view_url = null;
        if ("service" in this.node.data)
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

        d3.html(view_url, {credentials: "include"}).then(html => this._got_quickinfo(html));
    }

    _get_details_url() {
        if (this.node.data.service && this.node.data.service != "") {
            return (
                "view.py?view_name=service" +
                "&host=" +
                encodeURIComponent(this.node.data.hostname) +
                "&service=" +
                encodeURIComponent(this.node.data.service)
            );
        } else {
            return "view.py?view_name=host&host=" + encodeURIComponent(this.node.data.hostname);
        }
    }
}

node_visualization_utils.node_type_class_registry.register(BILeafNode);

class BIAggregatorNode extends node_visualization_viewport_utils.AbstractGUINode {
    static id() {
        return "bi_aggregator";
    }
    constructor(nodes_layer, node) {
        super(nodes_layer, node);
        this.radius = 12;
        if (!this.node.parent)
            // the root node gets a bigger radius
            this.radius = 16;
    }

    _get_basic_quickinfo() {
        let quickinfo = [];
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

    get_context_menu_elements() {
        let elements = [];

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
                    this.viewport.recompute_node_chunk_descendants_and_links(this.node.data.chunk);
                    this.viewport.update_layers();
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
                this.viewport.recompute_node_chunk_descendants_and_links(this.node.data.chunk);
                this.viewport.update_layers();
            },
            href: "",
            img: "themes/facelift/images/icon_expand.png",
        });

        elements.push({
            text: "Below this node, show only problems",
            on: event => {
                event.stopPropagation();
                this._filter_root_cause(this.node);
                this.viewport.recompute_node_chunk_descendants_and_links(this.node.data.chunk);
                this.viewport.update_layers();
            },
            img: "themes/facelift/images/icon_error.png",
        });
        return elements;
    }
}
node_visualization_utils.node_type_class_registry.register(BIAggregatorNode);

class NodeLink {
    constructor(nodes_layer, link_data) {
        this.nodes_layer = nodes_layer;
        this.viewport = nodes_layer.viewport;
        this.link_data = link_data;
        this.selection = null;

        this._line_config = this.link_data.source.data.chunk.layout_settings.config.line_config;
    }

    id() {
        return [this.link_data.source.data.id, this.link_data.target.data.id];
    }

    render_into(selection) {
        switch (this._line_config.style) {
            case "straight": {
                this.selection = selection
                    .append("line")
                    .classed("link_element", true)
                    .attr("marker-end", "url(#triangle)")
                    .attr("stroke-width", function (d) {
                        return Math.max(1, 2 - d.depth);
                    })
                    .style("stroke", "darkgrey");
                break;
            }
            default: {
                this.selection = selection
                    .append("path")
                    .classed("link_element", true)
                    .attr("fill", "none")
                    .attr("stroke-width", 1)
                    .style("stroke", "darkgrey");
                break;
            }
        }
        if (this._line_config.dashed) this.selection.classed("dashed", true);
    }

    update_position(enforce_transition = false) {
        let source = this.link_data.source;
        let target = this.link_data.target;
        let force_type = node_visualization_layout_styles.LayoutStyleForce.prototype.type();

        let is_force =
            source.data.current_positioning.type == force_type ||
            target.data.current_positioning.type == force_type;
        if (
            source.data.transition_info.use_transition ||
            target.data.transition_info.use_transition ||
            is_force
        )
            this.selection.interrupt();

        if (this.selection.attr("in_transit") > 0 && !is_force) {
            return;
        }

        if (source.data.current_positioning.hide_node_link) {
            this.selection.attr("opacity", 0);
            return;
        }
        this.selection.attr("opacity", 1);

        let x1 = source.data.target_coords.x;
        let y1 = source.data.target_coords.y;
        let x2 = target.data.target_coords.x;
        let y2 = target.data.target_coords.y;

        let tmp_selection = this.add_optional_transition(this.selection);
        switch (this._line_config.style) {
            case "straight": {
                tmp_selection.attr("x1", x1).attr("y1", y1).attr("x2", x2).attr("y2", y2);
                break;
            }
            case "round": {
                tmp_selection.attr("d", d => this.diagonal_line(x1, y1, x2, y2));
                break;
            }
            case "elbow": {
                tmp_selection.attr("d", d => this.elbow(x1, y1, x2, y2));
                break;
            }
        }
    }

    elbow(source_x, source_y, target_x, target_y) {
        return "M" + source_x + "," + source_y + "V" + target_y + "H" + target_x;
    }

    // Creates a curved (diagonal) path from parent to the child nodes
    diagonal_line(source_x, source_y, target_x, target_y) {
        let s = {};
        let d = {};
        s.y = source_x;
        s.x = source_y;
        d.y = target_x;
        d.x = target_y;

        let path = `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                  ${(s.y + d.y) / 2} ${d.x},
                  ${d.y} ${d.x}`;

        return path;
    }

    add_optional_transition(selection) {
        let source = this.link_data.source;
        let target = this.link_data.target;
        if (
            (!source.data.transition_info.use_transition &&
                !target.data.transition_info.use_transition) ||
            this.viewport.layout_manager.dragging
        )
            return selection;

        return node_visualization_utils.DefaultTransition.add_transition(
            selection.attr("in_transit", 100)
        )
            .on("end", d => {})
            .attr("in_transit", 0)
            .on("interrupt", () => {
                node_visualization_utils.log(7, "link update position interrupt");
                this.selection.attr("in_transit", 0);
            })
            .attr("in_transit", 0);
    }
}

export class LayeredNodesLayer extends node_visualization_viewport_utils.LayeredLayerBase {
    id() {
        return "nodes";
    }

    name() {
        return "Nodes Layer";
    }

    constructor(viewport) {
        super(viewport);
        this.last_scale = 1;
        // Node instances by id
        this.node_instances = {};
        // NodeLink instances
        this.link_instances = {};

        this.nodes_selection = null;
        this.links_selection = null;
        this.popup_menu_selection = null;
    }

    setup() {
        // Nodes/Links drawn on screen
        this.links_selection = this.selection
            .append("g")
            .attr("name", "viewport_layered_links")
            .attr("id", "links");
        this.nodes_selection = this.selection
            .append("g")
            .attr("name", "viewport_layered_nodes")
            .attr("id", "nodes");
    }

    render_line_style(into_selection) {
        let line_style_div = into_selection.selectAll("select").data([null]);

        let line_style_div_enter = line_style_div.enter();
        let row_enter = line_style_div_enter.append("table").append("tr");
        row_enter.append("td").text("Line style");

        let select = row_enter
            .append("select")
            .style("pointer-events", "all")
            .style("width", "200px");

        let options = select
            .on("change", event => this._change_line_style(event))
            .selectAll("option")
            .data(["straight", "round", "elbow"]);
        options.exit().remove();
        options = options.enter().append("option").merge(options);

        let current_style = "round";
        this.viewport.get_hierarchy_list().forEach(node_chunk => {
            current_style = node_chunk.layout_settings.config.line_config.style;
        });

        options
            .property("value", d => d)
            .property("selected", d => d == current_style)
            .text(d => d);
    }

    _change_line_style(event) {
        let new_line_style = d3.select(event.target).property("value");
        this.viewport.get_hierarchy_list().forEach(node_chunk => {
            node_chunk.layout_instance.line_config.style = new_line_style;
            node_chunk.layout_settings.config.line_config.style = new_line_style;
        });

        this.links_selection
            .selectAll(".link_element")
            .each(link_data => this._remove_link(link_data))
            .remove();
        this.update_data();
        this.update_gui(true);
    }

    zoomed() {
        let transform_text =
            "translate(" + this.viewport.last_zoom.x + "," + this.viewport.last_zoom.y + ")";
        this.selection.attr("transform", transform_text);

        // Interrupt any gui transitions whenever the zoom factor is changed
        if (this.last_scale != this.viewport.last_zoom.k)
            this.selection.selectAll(".node_element, .link_element").interrupt();

        for (let idx in this.node_instances) this.node_instances[idx].update_quickinfo_position();

        if (this.last_scale != this.viewport.last_zoom.k) this.update_gui(true);

        this.last_scale = this.viewport.last_zoom.k;
    }

    update_data() {
        this._update_links();
        this._update_nodes();
    }

    _update_nodes() {
        let visible_nodes = this.viewport.get_all_nodes().filter(d => !d.data.invisible);
        let nodes_selection = this.nodes_selection
            .selectAll(".node_element")
            .data(visible_nodes, d => d.data.id);

        // Create new nodes
        nodes_selection.enter().each((node_data, idx, node_list) => {
            this._create_node(node_data).render_into(d3.select(node_list[idx]));
        });
        // Existing nodes: Update bound data in all nodes
        nodes_selection.each((node_data, idx, node_list) =>
            this._update_node(node_data, d3.select(node_list[idx]))
        );
        // Remove obsolete nodes
        nodes_selection
            .exit()
            .each(node_data => this._remove_node(node_data))
            .classed("node_element", false)
            .transition()
            .attr("transform", node => {
                // Move vanishing nodes, back to their parent nodes
                if (node.parent) return node.parent.selection.attr("transform");
                else return node.selection.attr("transform");
            })
            .style("opacity", 0)
            .remove();
    }

    _update_links() {
        let links = this.viewport.get_all_links();
        let links_selection = this.links_selection
            .selectAll(".link_element")
            .data(links, d => [d.source.data.id, d.target.data.id]);
        links_selection
            .enter()
            .each((link_data, idx, links) => this._create_link(link_data, d3.select(links[idx])));
        links_selection.each((link_data, idx, links) =>
            this._update_link(link_data, d3.select(links[idx]))
        );
        links_selection
            .exit()
            .each(link_data => this._remove_link(link_data))
            .remove();
    }

    _create_node(node_data) {
        let node_class = node_visualization_utils.node_type_class_registry.get_node_class(
            node_data.data.node_type
        );
        let new_node = new node_class(this, node_data);
        this.node_instances[new_node.id()] = new_node;
        return new_node;
    }

    _update_node(node_data, selection) {
        selection.selectAll("*").each(function (d) {
            d3.select(this).datum(node_data);
        });
        this.node_instances[node_data.data.id].update_node_data(node_data, selection);
    }

    _remove_node(node_data) {
        delete this.node_instances[node_data.data.id];
    }

    _create_link(link_data, selection) {
        let new_link = new NodeLink(this, link_data);
        this.link_instances[new_link.id()] = new_link;
        new_link.render_into(selection);
    }

    _update_link(link_data, selection) {
        selection.selectAll("*").each(function (d) {
            d3.select(this).datum(node_data);
        });
        // TODO: provide a function within the link instance to update its data
        this.link_instances[[link_data.source.data.id, link_data.target.data.id]].link_data =
            link_data;
    }

    _remove_link(link_data) {
        delete this.link_instances[[link_data.source.data.id, link_data.target.data.id]];
    }

    update_gui(force = false) {
        this._update_position_of_context_menu();
        if (
            !force &&
            node_visualization_layout_styles.force_simulation._simulation.alpha() < 0.11
        ) {
            for (let idx in this.node_instances)
                this.node_instances[idx].node.data.transition_info.use_transition = false;
            return;
        }

        for (let idx in this.node_instances) this.node_instances[idx].update_position();

        for (let idx in this.link_instances) this.link_instances[idx].update_position();

        // Disable node transitions after each update step
        for (let idx in this.node_instances)
            this.node_instances[idx].node.data.transition_info.use_transition = false;
    }

    render_context_menu(event, node_instance) {
        if (!this.viewport.layout_manager.edit_layout && !node_instance) return; // Nothing to show

        let node = null;
        let coords = {};
        if (node_instance) {
            node = node_instance.node;
            coords = node;
        } else {
            let last_zoom = this.viewport.last_zoom;
            coords = {
                x: (event.layerX - last_zoom.x) / last_zoom.k,
                y: (event.layerY - last_zoom.y) / last_zoom.k,
            };
        }

        event.preventDefault();
        event.stopPropagation();

        // TODO: remove this, apply general update pattern..
        this.div_selection.selectAll("#popup_menu").remove();

        // Create menu
        this.popup_menu_selection = this.div_selection.selectAll("#popup_menu").data([coords]);
        this.popup_menu_selection = this.popup_menu_selection
            .enter()
            .append("div")
            .attr("id", "popup_menu")
            .style("pointer-events", "all")
            .style("position", "absolute")
            .classed("popup_menu", true)
            .merge(this.popup_menu_selection);

        // Setup ul
        let content = this.popup_menu_selection.selectAll(".content ul").data([null]);
        content = content
            .enter()
            .append("div")
            .classed("content", true)
            .append("ul")
            .merge(content);

        // Create li for each item
        if (this.viewport.layout_manager.edit_layout) {
            // Add elements layout manager
            this._add_elements_to_context_menu(
                content,
                "layouting",
                this.viewport.layout_manager.get_context_menu_elements(node)
            );
            // TODO: apply GUP
            if (node_instance) content.append("li").append("hr");
        }

        if (node_instance)
            // Add elements from node
            this._add_elements_to_context_menu(
                content,
                "node",
                node_instance.get_context_menu_elements()
            );

        if (content.selectAll("li").empty()) this.popup_menu_selection.remove();
        else this._update_position_of_context_menu();
    }

    _add_elements_to_context_menu(content, element_source, elements) {
        let links = content.selectAll("li" + "." + element_source).data(elements);
        links.exit().remove();

        links = links
            .enter()
            .append("li")
            .classed(element_source, true)
            .append("a")
            .classed("noselect", true);

        // Add optional href
        links.each((d, idx, nodes) => {
            if (d.href) {
                d3.select(nodes[idx])
                    .attr("href", d.href)
                    .on("click", () => this.remove_context_menu());
            }
        });

        // Add optional img
        links.each(function (d) {
            if (d.img) {
                d3.select(this).append("img").classed("icon", true).attr("src", d.img);
            }
        });

        // Add text
        links.each(function (d) {
            d3.select(this).append("div").style("display", "inline-block").text(d.text);
        });

        // Add optional click handler
        links.each((d, idx, nodes) => {
            if (d.on) {
                d3.select(nodes[idx]).on("click", event => {
                    d.on(event);
                    this.remove_context_menu();
                });
            }
        });
    }

    _update_position_of_context_menu() {
        if (this.popup_menu_selection == null) return;

        // Search menu
        let popup_menu = this.popup_menu_selection;
        if (popup_menu.empty()) return;

        // Set position
        let old_coords = popup_menu.datum();

        let new_coords = this.viewport.translate_to_zoom(old_coords);

        popup_menu.style("left", new_coords.x + "px").style("top", new_coords.y + "px");
    }

    remove_context_menu() {
        this.div_selection.select("#popup_menu").remove();
    }
}

node_visualization_utils.layer_registry.register(LayeredIconOverlay, 10);
node_visualization_utils.layer_registry.register(LayeredDebugLayer, 20);
node_visualization_utils.layer_registry.register(LayeredNodesLayer, 50);
