/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export function get(name: string): string {
    return default_lookup[name] || "MISSING TRANSLATION";
}

const default_lookup: Record<string, string> = {
    selected_style_configuration: "Selected style configuration",
    advanced_configuration_options: "Advanced configuration options",
    show_force_configuration: "Show force configuration",
    layout_configuration: "Layout configuration",
    remove_style: "Remove style",
    remove_all_styles: "Remove all styles",
    convert_to: "Convert to",
    convert_all_nodes_to: "Convert all nodes to",
    viewport_information: "Viewport information",
    zoom: "Zoom",
    panning: "Panning",
    mouse_position: "Mouse position",
    reset: "Reset",
    coordinates: "Coordinates",
    save: "Save",
    save_aggregation: "Save as new layout for this aggregation",
    delete_layout: "Reset to default layout",
    zoom_reset: "Reset zoom",
    zoom_fit: "Fit to screen",
    show: "Show",
    hide: "Hide",
    host_labels: "host name",
    service_labels: "service name",
    icons: "Icons",
    line_style: "Line style",
    round: "Round",
    straight: "Straight",
    elbow: "Elbow",
    all: "All",
    none: "None",
    only_problems: "Only problems",
    services: "Services",
    merge_data: "Merge nodes with equal ID",
    set_root_node: "Only grow from here",
    add_root_node: "Additionally grow from here",
    remove_root_node: "Do not grow from here",
    matching_nodes: "Matching nodes",
};
