#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.breadcrumb import make_simple_page_breadcrumb
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.pages import Page, PageRegistry, PageResult


class GuiTimingsPage(Page):
    def _title(self) -> str:
        return "GUI timings"

    def page(self) -> PageResult:  # pylint: disable=useless-return
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry["help_links"], _("Info"))
        make_header(
            html,
            self._title(),
            breadcrumb=breadcrumb,
        )
        html.javascript(
            """



function min(numbers) {
    if (!numbers.length) {
        return 0;
    }
    return Math.min(...numbers);
}


function max(numbers) {
    if (!numbers.length) {
        return 0;
    }
    return Math.max(...numbers);
}


function mean(numbers) {
    if (!numbers.length) {
        return 0;
    }
    return numbers.reduce((sum, value) => sum + value, 0) / numbers.length;
}


function median(numbers) {
    if (!numbers.length) {
        return 0;
    }
    const sortedNumbers = [...numbers].sort((a, b) => a - b);
    const mid = Math.floor(sortedNumbers.length / 2);
    if (sortedNumbers.length % 2 !== 0) {
        // The middle number.
        return sortedNumbers[mid];
    } else {
        // Average of the middle two numbers.
        return (sortedNumbers[mid - 1] + sortedNumbers[mid]) / 2;
    }
}


function stddev(numbers) {
    if (!numbers.length) {
        return 0;
    }
    const meanValue = mean(numbers);
    return Math.sqrt(
        numbers.reduce((sum, value) => sum + Math.pow(value - meanValue, 2), 0) / numbers.length
    );
}

function coefficientOfVariation(numbers) {
    if (numbers.length === 0) {
        return 0;
    }
    const meanValue = mean(numbers);
    if (meanValue === 0) {
        return 0;
    }
    const stddevValue = stddev(numbers);
    return stddevValue / meanValue;
}


function decimals(num, unit) {
    const result = Math.round(num * 100) / 100;
    return `${result}${unit}`
}


function calculateStats(numbers) {
    return {
        min: decimals(min(numbers), "ms"),
        max: decimals(max(numbers), "ms"),
        mean: decimals(mean(numbers), "ms"),
        median: decimals(median(numbers), "ms"),
        stddev: decimals(stddev(numbers), ""),
        coefficientOfVariation: decimals(coefficientOfVariation(numbers), ""),
        records: numbers.length,
    }
}


function groupedResults(db) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([metricsTable], 'readwrite');
        const store = transaction.objectStore(metricsTable);
        let allRecords = store.getAll();
        allRecords.onsuccess = function(event) {
            let grouped = Object.groupBy(allRecords.result, ({ url }) => url);
            resolve(grouped);
        };
        allRecords.onerror = (event) => {
            reject(event.target.error);
        };
    });
}


function tabulate(element, data, columns) {
    const table = element
        .append('table')
        .attr("class", "data table");

    const tbody = table.append('tbody');

    const thead = table
      .append('thead')
      .append('tr')
      .selectAll('th')
      .data(columns)
      .enter()
      .append('th')
      .text((column) => column);

    const rows = tbody
      .selectAll('tr')
      .data(data)
      .enter()
      .append('tr')
      .attr("class", "data");

    // create a cell in each row for each column
    const cells = rows
        .selectAll('td')
        .data(function (row) {
            return columns.map((column) => {
                return {
                    column: column,
                    value: row[column],
                };
            });
      })
      .enter()
      .append('td')
      .text((d) => d.value);

    return table;
}


document.addEventListener("DOMContentLoaded", async () => {
    const repeatUrlsTable = "repeatUrls";
    const metricsTable = "metrics";

    // We use a database!
    function openDatabase() {
        // Whenever we need to change the schema, increment the version here.
        const dbVersion = 1;
        const dbName = 'PageMetricsDB';

        return new Promise((resolve, reject) => {
            const openRequest = indexedDB.open(dbName, dbVersion);

            openRequest.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(metricsTable)) {
                    const objectStore = db.createObjectStore(metricsTable, { autoIncrement: true });
                    objectStore.createIndex('url', 'url', { unique: false });
                    objectStore.createIndex('metricName', 'metricName', { unique: false });
                }
                if (!db.objectStoreNames.contains(repeatUrlsTable)) {
                    const objectStore = db.createObjectStore(repeatUrlsTable, { keyPath: "url" });
                }
            };

            openRequest.onsuccess = (event) => resolve(event.target.result);
            openRequest.onerror = (event) => reject(event.target.error);
        });
    }
    let db = await openDatabase();
    const results = await groupedResults(db);
    const histograms = d3.select("#histograms");
    for (let url of Object.keys(results).sort((a, b) => a.localeCompare(b))) {
        histograms
            .append("h3")
            .append("a")
            .attr("href", url)
            .text(`${url}`);
        let stats = [];
        for (let metric of ["fullyLoaded", "fullyRendered"]) {
             stats.push(
                {
                    metric: metric,
                    ...calculateStats(
                        results[url]
                            .filter((entry) => entry.metricName == metric)
                            .map((entry) => entry.loadTime)
                    ),
                }
             );
        }
        tabulate(
            histograms,
            stats,
            [
                "metric",
                "min",
                "max",
                "mean",
                "median",
                "stddev",
                "coefficientOfVariation",
                "records",
            ],
        );
    }
});

"""
        )

        html.open_div(id_="info_title")
        html.h1("Client side GUI timings")
        html.close_div()

        html.div(None, id_="info_underline")

        html.open_div(id_="histograms")
        html.close_div()

        html.close_div()
        return None


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page("gui_timings")(GuiTimingsPage)
