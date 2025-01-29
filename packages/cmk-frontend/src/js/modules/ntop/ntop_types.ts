/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {TableFigureData} from "@/modules/figures/cmk_table";

//cmk/gui/cee/ntop/type_check.py:109
export interface TopPeerProtocol {
    host: string;
    name: string;
    host_url: string;
    l7proto: string;
    l7proto_url: string;
    traffic: number;
    traffic_hr: string;
}

export interface NtopTabData {
    ntop_link: string;
}

//cmk.gui.cee.ntop.pages.AjaxNtopHostApplications
export interface ApplicationTabData extends NtopTabData {
    table_apps_overview: TableFigureData;
    table_apps_applications: TableFigureData;
    table_apps_categories: TableFigureData;
}

//cmk.gui.cee.ntop.pages.AjaxNtopHostTopPeersProtocols
export interface PeersTabData extends NtopTabData {
    stats: TopPeerProtocol[];
}

//cmk.gui.cee.ntop.pages.NtopHostPorts
export interface PortsTabData extends NtopTabData {
    table_ports: TableFigureData;
}

//cmk.gui.cee.ntop.pages.AjaxNtopGetIfTcpFlagsPktDistro
export interface PacketsTabData extends NtopTabData {
    table_packets: TableFigureData;
}

//cmk.gui.cee.ntop.pages.NtopInterfaceTraffic
export interface TrafficTabData extends NtopTabData {
    table_overview: TableFigureData;
    table_breakdown: TableFigureData;
}

//cmk.gui.cee.ntop.pages.AjaxNtopInterfaceStats
export interface HostTabData extends NtopTabData {
    rows: {cells: string[]}[];
    meta: {data: {ntop_host: string}}; //not very clear structure
    classes: string[];
}
