import * as d3 from "d3";
import * as cmk_figures from "cmk_figures";

export class HostStats extends cmk_figures.FigureBase {
    static ident() {
        return "hoststats";
    }

    initialize(debug) {
        super.initialize(debug);

        this._table_div = this._div_selection.append("div").classed("stats_table", true);
        this.svg = this._div_selection.append("svg");
        this._hexagon_box = this.svg.append("g").classed("hexagons", true);
    }

    update_data(data) {
        this._data = data.data;
    }

    update_gui() {
        if (!this._data || !this._data.total) return;

        this.resize();
        let parts = this._data.parts;
        const hexbin = d3.hexbin();
        let hexagon_config = [];

        let largest_element_count = 0;
        for (const element of this._data.parts) {
            if (element.count > largest_element_count) largest_element_count = element.count;
        }

        let sum = this._data.total.count;
        let radius = 0;
        parts.forEach(part => {
            radius = (Math.pow(sum, 0.33) / Math.pow(this._data.total.count, 0.33)) * 50;
            sum -= part.count;

            hexagon_config.push({
                title: part.title,
                path: hexbin.hexagon(radius),
                color: "#262f38",
                css_class: part.css_class,
                tooltip: "",
                count: part.count,
            });
        });

        // render all hexagons
        this._hexagon_box
            .selectAll("path.hexagon")
            .data(hexagon_config)
            .join(enter => enter.append("path").classed("hexagon", true))
            .attr("d", d => d.path)
            .attr("fill", d => d.color)
            .attr("class", d => "site_element " + d.css_class);

        // render table
        let table = this._table_div
            .selectAll("table")
            .data([parts.concat(this._data.total)])
            .join("table");
        let rows = table
            .selectAll("tr")
            .data(d => d)
            .join("tr");

        let a = rows.selectAll("td a").data(d => [
            {text: d.count, url: d.url, css_class: "count " + d.css_class},
            {text: d.title, url: d.url, css_class: "text"},
        ]);
        a.join(enter => enter.append("td").append("a"))
            .attr("class", d => d.css_class)
            .text(d => d.text)
            .attr("href", d => d.url);

        this.render_title(this._data.title);
    }
}

export class ServiceStats extends HostStats {
    static ident() {
        return "servicestats";
    }
}

cmk_figures.figure_registry.register(HostStats);
cmk_figures.figure_registry.register(ServiceStats);
