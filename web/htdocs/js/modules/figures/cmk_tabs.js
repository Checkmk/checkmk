import * as d3 from "d3";

export class TabsBar {
    constructor(div_selector) {
        this._div_selector = div_selector;
        this._div_selection = d3.select(this._div_selector);
        this._div_selection.classed("cmk_tab", true);
        this._tabs_by_id = {};
        this._tabs_list = [];
    }

    initialize() {
        this._nav = this._div_selection
            .append("nav")
            .attr("role", "navigation")
            .classed("main-navigation", true);
        this.main_content = this._div_selection.append("div").classed("main-content", true);

        this._register_tabs();

        this._ul = this._nav.append("ul");
        let a_selection = this._ul
            .selectAll("li")
            .data(this._tabs_list)
            .enter()
            .append("li")
            .each((d, idx, nodes) => {
                d3.select(nodes[idx]).classed(d.tab_id(), true);
            })
            .on("click", () => this._tab_clicked())
            .append("a")
            .attr("href", d => "#" + d.tab_id())
            .style("pointer-events", "none");

        a_selection
            .append("span")
            .classed("noselect", true)
            .text(d => d.name());
    }

    _register_tabs() {
        this._get_tab_entries().forEach(tab_class => {
            let new_tab = new tab_class(this);
            new_tab.initialize();
            this._tabs_by_id[new_tab.tab_id()] = new_tab;
            this._tabs_list.push(new_tab);
        });
    }

    get_tab_by_id(tab_id) {
        return this._tabs_by_id[tab_id];
    }

    _get_tab_entries() {
        return [];
    }

    _tab_clicked() {
        let target = d3.select(d3.event.target);
        let tab = target.datum();
        this._activate_tab(tab);
    }

    _activate_tab(tab) {
        let enable_tab_id = tab.tab_id();

        // Hide all tabs
        this._ul.selectAll("li").classed("active", false);
        this.main_content.selectAll(".cmk_tab_element").classed("active", false);

        // Deactivate other tabs
        for (let tab_id in this._tabs_list) {
            if (tab_id == enable_tab_id) continue;

            this._tabs_list[tab_id].deactivate();
        }

        // Enable selected tab
        this._ul.select("li." + enable_tab_id).classed("active", true);
        this.main_content.select("#" + enable_tab_id).classed("active", true);
        tab.activate();
    }
}

export class Tab {
    constructor(tabs_bar) {
        this._tabs_bar = tabs_bar;
        this._tab_selection = tabs_bar.main_content
            .append("div")
            .attr("id", this.tab_id())
            .classed("cmk_tab_element", true)
            .datum(this);
    }

    // Internal ID
    tab_id() {
        alert("tab id missing");
    }

    // Name in tab index
    name() {
        alert("tab name missing");
    }

    // Called upon instance creation
    initialize() {}

    // Called when the tab is activated
    activate() {}

    // Called when the tab is deactivated
    deactivate() {}
}
