// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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

// Takes care of all available datasources
// Offers register and get methods for datasource
// Prevents duplicate instantiations of same datasources
export class DatasourceManager {
    constructor() {
        // Datasources lookup {id: instance}
        this.datasources = {};
        this._initialize_datasources();
        setInterval(() => this.schedule(true), 10000);
    }

    _initialize_datasources() {
        this._register_datasource(AggregationsDatasource);
        this._register_datasource(TopologyDatasource);
    }

    _register_datasource(datasource_class) {
        if (datasource_class.id() in this.datasources) return;
        this.datasources[datasource_class.id()] = new datasource_class();
    }

    schedule(enforce) {
        let now = Math.floor(new Date().getTime() / 1000);
        for (let idx in this.datasources) {
            let datasource = this.datasources[idx];
            if (datasource._enabled != true || datasource._supports_regular_updates != true)
                continue;
            if (
                enforce == true ||
                now - datasource._last_update > datasource.get_update_interval()
            ) {
                datasource.update_fetched_data();
            }
        }
    }

    get_datasource(datasource_id) {
        return this.datasources[datasource_id];
    }

    get_datasources() {
        return this.datasources;
    }
}

// Abstract base class for all datasources
export class AbstractDatasource {
    static id() {
        return "abstract_datasource";
    }

    constructor(description) {
        this.description = description;

        this._enabled = false;
        this._supports_regular_updates = true;
        this._update_interval = 30;
        this._last_update = 0;
        this._fetch_latency = 0;

        this._data = null;
        this._new_data_subscribers = [];

        this._fetch_url = null;
        this._fetch_params = null;
    }

    subscribe_new_data(func) {
        this._new_data_subscribers.push(func);
    }

    unsubscribe_new_data(func) {
        this._new_data_subscribers.splice(func, 1);
    }

    update_fetched_data() {
        this._fetch();
    }

    set_update_interval(value) {
        this._update_interval = value;
    }

    get_update_interval() {
        return this._update_interval;
    }

    enable() {
        this._enabled = true;
    }

    disable() {
        this._enabled = false;
    }

    fetch(url, params = {}) {
        this._fetch_start = Math.floor(new Date().getTime() / 1000);
        this._fetch_url = url;
        this._fetch_params = params;
        this._fetch();
    }

    _fetch(params = {}) {
        if (!this._fetch_url) return;
        d3.json(encodeURI(this._fetch_url), {
            credentials: "include",
            method: "POST",
            body: this._fetch_params,
            headers: {
                "Content-type": "application/x-www-form-urlencoded",
            },
        }).then(json_data => this._set_data(json_data));
    }

    get_data() {
        return this._data;
    }

    _set_data(new_data) {
        this._last_update = Math.floor(new Date().getTime() / 1000);
        this._fetch_latency = this._last_update - this._fetch_start;

        // TODO: check ajax result_code
        this._data = new_data.result;
        this._inform_subscribers();
    }

    _inform_subscribers() {
        this.generic_update_latency = +(new Date() - this.time_update_generic_data_start) / 1000;
        this._new_data_subscribers.forEach(subscriber => subscriber(this._data));
    }
}

export class AggregationsDatasource extends AbstractDatasource {
    static id() {
        return "bi_aggregations";
    }

    constructor() {
        super("Aggregation datasource");
        this._update_interval = 30;
    }

    fetch_aggregations(list_of_aggregations, use_layout_id) {
        let url =
            "ajax_fetch_aggregation_data.py?aggregations=" + JSON.stringify(list_of_aggregations);
        if (use_layout_id) url += "&layout_id=" + use_layout_id;
        this.fetch(url);
    }
}

export class TopologyDatasource extends AbstractDatasource {
    static id() {
        return "topology";
    }

    constructor() {
        super("Topology");
    }

    fetch_hosts(topology_settings) {
        let fetch_params = "topology_settings=" + JSON.stringify(topology_settings);
        this.fetch("ajax_fetch_topology.py", fetch_params);
    }
}
