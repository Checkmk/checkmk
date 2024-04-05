/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

//#.
//#   .-Datasource Manager-------------------------------------------------.
//#   |          ____        _                                             |
//#   |         |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___         |
//#   |         | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \        |
//#   |         | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/        |
//#   |         |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___|        |
//#   |                                                                    |
//#   |              __  __                                                |
//#   |             |  \/  | __ _ _ __   __ _  __ _  ___ _ __              |
//#   |             | |\/| |/ _` | '_ \ / _` |/ _` |/ _ \ '__|             |
//#   |             | |  | | (_| | | | | (_| | (_| |  __/ |                |
//#   |             |_|  |_|\__,_|_| |_|\__,_|\__, |\___|_|                |
//#   |                                       |___/                        |
//#   +--------------------------------------------------------------------+

import * as d3 from "d3";
import {SerializedNodevisLayout} from "nodevis/layout_utils";
import {
    DatasourceCallback,
    SerializedNodeConfig,
    TopologyFrontendConfig,
} from "nodevis/type_defs";
import {CMKAjaxReponse} from "types";

import * as utils from "../utils";

interface AjaxFetchTopologyData {
    node_config: SerializedNodeConfig;
    layout?: SerializedNodevisLayout;
    headline: string;
    errors: string[];
    frontend_configuration: TopologyFrontendConfig;
    query_hash?: string;
}

// Takes care of all available datasources
// Offers register and get methods for datasource
// Prevents duplicate instantiations of same datasources
export class DatasourceManager {
    datasources: {[name: string]: AbstractDatasource};

    constructor() {
        // Datasources lookup {id: instance}
        this.datasources = {};
        this._initialize_datasources();
        setInterval(() => this.schedule(true), 30000);
    }

    _initialize_datasources(): void {
        this._register_datasource(AggregationsDatasource);
        this._register_datasource(TopologyDatasource);
    }

    _register_datasource(datasource_class: typeof AbstractDatasource): void {
        if (datasource_class.id() in this.datasources) return;
        this.datasources[datasource_class.id()] = new datasource_class();
    }

    schedule(enforce = false): void {
        if (!utils.is_window_active()) return;
        const now = Math.floor(new Date().getTime() / 1000);
        for (const idx in this.datasources) {
            const datasource = this.datasources[idx];
            if (!datasource._enabled || !datasource._supports_regular_updates)
                continue;
            if (
                enforce ||
                now - datasource._last_update > datasource.get_update_interval()
            ) {
                datasource.update_fetched_data();
            }
        }
    }

    get_datasource(datasource_id: string): AbstractDatasource {
        return this.datasources[datasource_id];
    }

    get_datasources(): {[name: string]: AbstractDatasource} {
        return this.datasources;
    }
}

// Abstract base class for all datasources
export class AbstractDatasource extends Object {
    _enabled = false;
    _supports_regular_updates = true;
    _update_interval = 30;
    _last_update = 0;
    _fetch_latency = 0;
    _data: any = null;
    _new_data_subscribers: DatasourceCallback[] = [];
    _fetch_url: string | null = null;
    _fetch_params: BodyInit | null = null;
    _fetch_start = 0;

    static id(): string {
        return "abstract_datasource";
    }

    subscribe_new_data(func: DatasourceCallback): void {
        this._new_data_subscribers.push(func);
    }

    unsubscribe_new_data(func: number): void {
        this._new_data_subscribers.splice(func, 1);
    }

    update_fetched_data(): void {
        this._fetch();
    }

    set_update_interval(value: number): void {
        this._update_interval = value;
    }

    get_update_interval(): number {
        return this._update_interval;
    }

    enable(): void {
        this._enabled = true;
    }

    disable(): void {
        this._enabled = false;
    }

    fetch(url: string, params: BodyInit | null = null): void {
        this._fetch_start = Math.floor(new Date().getTime() / 1000);
        this._fetch_url = url;
        this._fetch_params = params;
        this._fetch();
    }

    _fetch(): void {
        if (!this._fetch_url) return;
        d3.json(encodeURI(this._fetch_url), {
            credentials: "include",
            method: "POST",
            body: this._fetch_params,
            headers: {
                "Content-type": "application/x-www-form-urlencoded",
            },
        }).then(json_data =>
            this._set_data(
                json_data as unknown as CMKAjaxReponse<AjaxFetchTopologyData>
            )
        );
    }

    get_data(): Record<string, any> {
        return this._data;
    }

    _set_data(new_data: CMKAjaxReponse<AjaxFetchTopologyData>): void {
        this._last_update = Math.floor(new Date().getTime() / 1000);
        this._fetch_latency = this._last_update - this._fetch_start;

        // TODO: check ajax result_code
        this._data = new_data.result;
        this._inform_subscribers();
    }

    _inform_subscribers(): void {
        this._new_data_subscribers.forEach(subscriber =>
            subscriber(this._data)
        );
    }
}

export class AggregationsDatasource extends AbstractDatasource {
    constructor() {
        super("Aggregation datasource");
        this._update_interval = 30;
    }

    static override id(): string {
        return "bi_aggregations";
    }

    fetch_aggregations(
        list_of_aggregations: string[],
        use_layout_id: string
    ): void {
        let url =
            "ajax_fetch_aggregation_data.py?aggregations=" +
            JSON.stringify(list_of_aggregations);
        if (use_layout_id) url += "&layout_id=" + use_layout_id;
        this.fetch(url);
    }
}

export class TopologyDatasource extends AbstractDatasource {
    constructor() {
        super("Topology");
    }

    static override id(): string {
        return "topology";
    }

    fetch_hosts(fetch_params: BodyInit | null) {
        this.fetch("ajax_fetch_topology.py", fetch_params);
    }
}
