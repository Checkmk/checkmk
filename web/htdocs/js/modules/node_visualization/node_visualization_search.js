import * as d3 from "d3"
import * as node_visualization_toolbar_utils from "node_visualization_toolbar_utils"


export class SearchAggregationsPlugin extends node_visualization_toolbar_utils.ToolbarPluginBase {
    id() {
        return "bi_search_aggregations"
    }

    constructor(main_instance) {
        super("Search aggr", main_instance)
        this.search_node_text = ""
        this.active = true
    }

    has_toggle_button() {
        return false
    }

    render_content() {
        this.content_selection.append("div")
                .classed("box", true)
                .classed("toolbar_search", true)
                .append("input").on("input", () => this.updated_search_node_text())
                      .classed("search_node", true)
                      .attr("placeholder", "Search node")
                      .attr("value", this.search_node_text)
    }

    updated_search_node_text() {
        this.set_search_node_text(d3.select(d3.event.target).property("value"))
        this.start_node_search()
    }

    set_search_node_text(text) {
        this.search_node_text = text
    }

    start_node_search() {
        if (this.search_node_text == "") {
            this.main_instance.infobox.feed_data([])
            return
        }

        let results = []
        let search_node_text_lower = this.search_node_text.trim().toLowerCase()
        this.main_instance.viewport.current_viewport.get_all_nodes().forEach(node=>{
            if (node.data.name.toLowerCase().search(search_node_text_lower) != -1) {
                results.push({"name": node.data.name, "state": node.data.state})
            }
        })

        let data = []
        data.datasource = this.id()
        data.type = "node"
        data.entries = results
        this.main_instance.infobox.feed_data(data)
    }
}

