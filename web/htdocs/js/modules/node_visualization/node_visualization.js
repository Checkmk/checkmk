
import * as node_visualization_toolbar from "node_visualization_toolbar"
import * as node_visualization_datasources from "node_visualization_datasources"
import * as node_visualization_viewport from "node_visualization_viewport"
import * as node_visualization_infobox from "node_visualization_infobox"
import * as d3 from "d3";

//
//  .--MainInstance--------------------------------------------------------.
//  |     __  __       _       ___           _                             |
//  |    |  \/  | __ _(_)_ __ |_ _|_ __  ___| |_ __ _ _ __   ___ ___       |
//  |    | |\/| |/ _` | | '_ \ | || '_ \/ __| __/ _` | '_ \ / __/ _ \      |
//  |    | |  | | (_| | | | | || || | | \__ \ || (_| | | | | (_|  __/      |
//  |    |_|  |_|\__,_|_|_| |_|___|_| |_|___/\__\__,_|_| |_|\___\___|      |
//  |                                                                      |
//  +----------------------------------------------------------------------+

class NodeVisualization {
    constructor(div_id) {
        this.div_id = div_id;

        this.div_selection = null
        this.datasource_manager = null
        this.viewport = null
        this.infobox = null
        this.toolbar = null

        this._initialize_components()

        // Fetch initial data
        this.datasource_manager.schedule()
    }

    _initialize_components() {
        this.div_selection = d3.select("#" + this.div_id).append("div")
                                        .attr("id", "node_visualization_root_div")
                                        .attr("div_id", this.div_id)
                                        .classed("node_vis", true) // Main indicator for most NodeVisualization css styles

        this.datasource_manager = new node_visualization_datasources.DatasourceManager()
        this.viewport = new node_visualization_viewport.Viewport(this)
        this.infobox = new node_visualization_infobox.InfoBox(this)
        this.toolbar = new node_visualization_toolbar.Toolbar(this)
    }

    get_div_selection() {
        return this.div_selection;
    }
}


export class BIVisualization extends NodeVisualization {
    show_aggregations(list_of_aggregations, use_layout_id) {
        let aggr_ds = this.datasource_manager.get_datasource(node_visualization_datasources.AggregationsDatasource.id())
        aggr_ds.subscribe_new_data(d=>this._show_aggregations(list_of_aggregations))
        aggr_ds.fetch_aggregations(list_of_aggregations, use_layout_id)
    }

    _show_aggregations(list_of_aggregations) {
        let aggr_ds = this.datasource_manager.get_datasource(node_visualization_datasources.AggregationsDatasource.id())
        let fetched_data = aggr_ds.get_data()

        let data_to_show = {chunks: []}
        for (let idx in fetched_data["aggregations"]) {
            data_to_show.chunks.push(fetched_data["aggregations"][idx])
        }

        if (fetched_data.use_layout)
            data_to_show.use_layout = fetched_data.use_layout

        this.viewport.show_data("bi_aggregations", data_to_show)
    }
}


export class NetworkTopologyVisualization extends NodeVisualization {
    show_network_topology(list_of_hosts) {
        let topo_ds = this.datasource_manager.get_datasource(node_visualization_datasources.NetworkTopologyDatasource.id())
        topo_ds.subscribe_new_data(d=>this._show_network_topology(list_of_hosts))
        topo_ds.fetch_hosts(list_of_hosts)
    }

    _show_network_topology(list_of_hosts) {
        let topo_ds = this.datasource_manager.get_datasource(node_visualization_datasources.NetworkTopologyDatasource.id())
        let topology_data = topo_ds.get_data()["topology_chunks"]

        let data_to_show = {chunks: []}
        for (let idx in topology_data) {
            data_to_show.chunks.push(topology_data[idx])
        }
        this.viewport.show_data("network_topology", data_to_show)
    }
}
