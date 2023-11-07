/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface VueComponentSpec {
    component_type: string;
    title: string;
    help: string;
    validation_errors: string[];
    config: {[name: string]: any};
}

export interface VueFormSpec {
    id: string;
    component: VueComponentSpec;
}

export interface IComponent {
    collect: () => any;
    debug_info: () => void;
}
