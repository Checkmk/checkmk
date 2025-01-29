/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {select} from "d3";

import type {metricsEntry} from "./tracking_database";
import {metricsTable, onError, openDatabase} from "./tracking_database";

type GroupedResult = {
    [key: string]: metricsEntry[];
};

type Section = {
    url: string;
    records: metricsEntry[];
    updated: number;
};

function customMetrics(entries: metricsEntry[]): string[] {
    const result: string[] = [];
    for (const metric of entries) {
        if (
            !metric.metricName.startsWith("rendered[") &&
            !result.includes(metric.metricName)
        ) {
            result.push(metric.metricName);
        }
    }
    return result;
}

function internalMetrics(entries: metricsEntry[]): string[] {
    const result: string[] = [];
    for (const metric of entries) {
        if (
            metric.metricName.startsWith("rendered[") &&
            !result.includes(metric.metricName)
        ) {
            result.push(metric.metricName);
        }
    }
    return result;
}

function timeSince(timestamp: number): string {
    type TimeUnit = {
        name: string;
        seconds: number;
    };

    const units: TimeUnit[] = [
        {name: "year", seconds: 31536000},
        {name: "month", seconds: 2592000},
        {name: "day", seconds: 86400},
        {name: "hour", seconds: 3600},
        {name: "minute", seconds: 60},
        {name: "second", seconds: 1},
    ];

    let elapsed = Math.floor((Date.now() - timestamp) / 1000); // Total seconds elapsed
    const parts: string[] = [];

    for (const unit of units) {
        const unitCount = Math.floor(elapsed / unit.seconds);
        if (unitCount > 0) {
            parts.push(
                `${unitCount} ${unitCount > 1 ? unit.name + "s" : unit.name}`,
            );
            elapsed -= unitCount * unit.seconds;
        }
        if (parts.length === 2) break; // Stop after adding two parts
    }

    return parts.length > 0 ? parts.join(", ") + " ago" : "just now";
}

export async function render_stats_table(dom_element: HTMLElement) {
    const node = select(dom_element);
    const columnsNames = [
        "metric",
        "min",
        "max",
        "mean",
        "median",
        "stddev",
        "coefficientOfVariation",
        "records",
    ];

    const db = await openDatabase();
    const results = await groupedResults(db);
    const sections = sortKeysByLastUpdated(results);
    for (const section of sections) {
        node.append("h3").html(
            `<a href="${section.url}">${
                section.url
            }</a> - last updated ${timeSince(section.updated)}. ${
                section.records.length
            } records.`,
        );
        const table = node.append("table").attr("class", "data table");

        const tbody_stats: {[index: string]: string}[] = [];
        const tfoot_stats: {[index: string]: string}[] = [];
        for (const metric of customMetrics(section.records)) {
            tbody_stats.push({
                metric: metric,
                ...calculateStats(
                    section.records
                        .filter(
                            (entry: metricsEntry) => entry.metricName == metric,
                        )
                        .map((entry: metricsEntry) => entry.loadTime),
                ),
            });
        }

        for (const metric of internalMetrics(section.records)) {
            tfoot_stats.push({
                metric: metric,
                ...calculateStats(
                    section.records
                        .filter(
                            (entry: metricsEntry) => entry.metricName == metric,
                        )
                        .map((entry: metricsEntry) => entry.loadTime),
                ),
            });
        }

        const headerRow = table.append("thead").append("tr");
        columnsNames.forEach(column => {
            headerRow.append("th").text(column);
        });

        const tbody = table.append("tbody");
        tbody_stats.forEach(row => {
            const tr = tbody.append("tr");
            columnsNames.forEach(value => {
                tr.append("td").attr("class", "data").text(row[value]);
            });
        });

        const tfoot = table.append("tfoot");
        tfoot_stats.forEach(row => {
            const tr = tfoot.append("tr");
            columnsNames.forEach(value => {
                tr.append("td").attr("class", "data").text(row[value]);
            });
        });
    }
}

// Taken from https://stackoverflow.com/a/62765924
/**
 * Generic grouping algorithm.
 * Takes a sequence and a closure which will applied to each entry in the
 * sequence and will return the grouping key for the entry.
 *
 * The sequence has to be pre-sorted by the grouping keys.
 */
const groupBy = <T, K extends keyof any>(list: T[], getKey: (item: T) => K) =>
    list.reduce(
        (previous, currentItem) => {
            const group = getKey(currentItem);
            if (!previous[group]) previous[group] = [];
            previous[group].push(currentItem);
            return previous;
        },
        {} as Record<K, T[]>,
    );

/**
 * Take the grouped result (grouped by URL), order them by last update and emit them as a list of objects.
 */
const sortKeysByLastUpdated = (data: GroupedResult): Section[] => {
    const timings = Object.entries(data).map(([key, records]) => {
        const highestTimestamp = records.reduce(
            (max, record) => Math.max(max, record.recordCreated),
            0,
        );
        return {key, highestTimestamp};
    });
    return timings
        .sort((a, b) => b.highestTimestamp - a.highestTimestamp)
        .map(entry => {
            return {
                url: entry.key,
                records: data[entry.key],
                updated: entry.highestTimestamp,
            };
        });
};

function groupedResults(db: IDBDatabase): Promise<GroupedResult> {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([metricsTable], "readwrite");
        const store = transaction.objectStore(metricsTable);
        const allRecords: IDBRequest<metricsEntry[]> = store.getAll();
        allRecords.onsuccess = (event: Event) => {
            const request = event.target as IDBRequest<metricsEntry[]>;
            const grouped = groupBy(
                request.result,
                (entry: metricsEntry) => entry.url,
            );
            resolve(grouped);
        };
        allRecords.onerror = onError<GroupedResult>(reject);
    });
}

function min(numbers: number[]): number {
    if (!numbers.length) {
        return 0;
    }
    return Math.min(...numbers);
}

function max(numbers: number[]): number {
    if (!numbers.length) {
        return 0;
    }
    return Math.max(...numbers);
}

function mean(numbers: number[]): number {
    if (!numbers.length) {
        return 0;
    }
    return numbers.reduce((sum, value) => sum + value, 0) / numbers.length;
}

function median(numbers: number[]): number {
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

function stddev(numbers: number[]): number {
    if (!numbers.length) {
        return 0;
    }
    const meanValue = mean(numbers);
    return Math.sqrt(
        numbers.reduce(
            (sum, value) => sum + Math.pow(value - meanValue, 2),
            0,
        ) / numbers.length,
    );
}

function coefficientOfVariation(numbers: number[]): number {
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

function decimals(num: number, unit: string): string {
    const result = Math.round(num * 100) / 100;
    return `${result}${unit}`;
}

function calculateStats(numbers: number[]): {[name: string]: string} {
    return {
        min: decimals(min(numbers), "ms"),
        max: decimals(max(numbers), "ms"),
        mean: decimals(mean(numbers), "ms"),
        median: decimals(median(numbers), "ms"),
        stddev: decimals(stddev(numbers), ""),
        coefficientOfVariation: decimals(coefficientOfVariation(numbers), ""),
        records: `${numbers.length}`,
    };
}
