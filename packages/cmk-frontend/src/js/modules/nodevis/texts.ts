/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export function get(key: keyof typeof default_lookup): string {
    return translations[key] || default_lookup[key] || "MISSING TRANSLATION";
}

let translations: Record<string, string> = {};

const default_lookup = {
    default: "Default",
    live_search: "Live search active",
    live_search_help:
        "Automatically detects changes in the formular and fetches new data",
    selected_style_configuration: "Selected style configuration",
    advanced_configuration_options: "Advanced configuration options",
    show_force_configuration: "Show gravity configuration",
    layout_configuration: "Layout configuration",
    remove_style: "Remove style",
    free_floating_style: "Free floating style",
    convert_to: "Change structure of this node to",
    convert_all_nodes_to: "Change structure of all nodes to",
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
    host_labels: "host names",
    service_labels: "service names",
    other_labels: "other names",
    icons: "Icons",
    line_style: "Line style",
    round: "Round",
    straight: "Straight",
    elbow: "Elbow",
    all: "All",
    none: "None",
    only_problems: "Only problems",
    show_services: "Show services",
    global_default: "Global default",
    services: "Services",
    merge_data: "Merge nodes with equal ID",
    set_root_node: "Replace hierarchical root with this node",
    add_root_node: "Add this node to existing root nodes",
    remove_root_node: "End growing here",
    matching_nodes: "Matching nodes",
    reference: "Reference",
    compare_to: "Compare to",
    missing_in_ref: "Missing in reference",
    only_in_ref: "Only in reference",
    flat: "Flat",
    full: "Full",
    hierarchy: "Hierarchy",
    allow_hops: "Allow growing here",
    forbid_hops: "Stop growing here",
    continue_hop: "Continue growth here",
    stop_continue_hop: "Do no longer continue here",
    unknown_service: "Unknown service",
    unknown_host: "Unknown host",
    host: "Host",
    service: "Service",
    host_details: "Host details",
    service_details: "Service details",
    icon_in_monitoring: "Icon in monitoring",
    can_grow_here: "Double-click to grow further",
    growth_stops_here: "Growth stops here",
    growth_continues_here: "Growth continues here",
};

export type TranslationKey = keyof typeof default_lookup;

export function set_translations(
    new_translations: Record<TranslationKey, string>,
) {
    translations = new_translations;
}
