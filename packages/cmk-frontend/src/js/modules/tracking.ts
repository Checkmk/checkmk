/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {metricsEntry, repeatUrlsEntry} from "./tracking_database";
import {
    addRecord,
    getRecord,
    metricsTable,
    onError,
    onSuccess,
    openDatabase,
    putRecord,
    repeatUrlsTable,
} from "./tracking_database";

export const currentUrl = window.location.pathname + window.location.search;

export async function activate_tracking(
    url: string,
    startTime: number,
    backendDuration: number,
) {
    // Expected to be called once all resources have been loaded.
    const fullyLoaded = Date.now() - startTime;
    // We set up the observer earlier so that its internal timing won't be delayed by our
    // following database work, etc.
    const mutationWaiter = waitForMutationsToStop(
        document.body,
        startTime,
        2000,
        isMouseoverMutation,
    );

    const db: IDBDatabase = await openDatabase();

    const repeat = await getRepeat(db, url);
    let prefix;
    if (repeat && repeat.times > 0) {
        prefix = `${repeat.metricPrefix}|`;
        console.warn(`Prefix ${repeat.metricPrefix} (${repeat.times} to go)`);
    } else {
        prefix = "";
    }

    await storePageLoadMetric(
        db,
        url,
        `${prefix}rendered[backend]`,
        backendDuration,
    );
    await storePageLoadMetric(
        db,
        url,
        `${prefix}rendered[backend+load]`,
        backendDuration + fullyLoaded,
    );
    const lastMutation = await mutationWaiter;
    await storePageLoadMetric(
        db,
        url,
        `${prefix}rendered[backend+load+mutations]`,
        backendDuration + lastMutation,
    );

    if (repeat && repeat.times > 0) {
        repeat.times -= 1;
        await setRepeat(db, repeat);
        window.location.reload();
    }
}

async function getRepeat(
    db: IDBDatabase,
    url: string,
): Promise<repeatUrlsEntry | null> {
    const transaction = db.transaction([repeatUrlsTable], "readwrite");
    const store = transaction.objectStore(repeatUrlsTable);
    return await getRecord<repeatUrlsEntry>(store, url);
}

async function setRepeat(
    db: IDBDatabase,
    repeat: repeatUrlsEntry,
): Promise<repeatUrlsEntry> {
    const transaction = db.transaction([repeatUrlsTable], "readwrite");
    const store = transaction.objectStore(repeatUrlsTable);
    return await putRecord<repeatUrlsEntry>(store, repeat);
}

async function storePageLoadMetric(
    db: IDBDatabase,
    url: string,
    metricName: string,
    loadTime: number,
) {
    const transaction = db.transaction([metricsTable], "readwrite");
    const store = transaction.objectStore(metricsTable);

    return await addRecord<metricsEntry>(store, {
        url: url,
        metricName: metricName,
        loadTime: loadTime,
        recordCreated: new Date().getTime(),
    });
}

type IsIgnoredMutation = (mutations: MutationRecord[]) => boolean;

function waitForMutationsToStop(
    observedElement: Node,
    startTime: number,
    timeoutDuration: number,
    isIgnoredMutation: IsIgnoredMutation,
): Promise<number> {
    return new Promise(resolve => {
        let lastMutationTime: number = Date.now();
        let timer: number;

        // console.log(`Setting up observer after ${lastMutationTime - startTime}ms`);
        timer = setTimeout(() => {
            resolve(lastMutationTime - startTime);
        }, timeoutDuration) as unknown as number;

        const observer = new MutationObserver((mutations: MutationRecord[]) => {
            lastMutationTime = Date.now();
            // console.log(`Got mutations after ${lastMutationTime - startTime}ms`);
            if (isIgnoredMutation(mutations)) return;

            clearTimeout(timer);
            timer = setTimeout(() => {
                observer.disconnect();
                resolve(lastMutationTime - startTime);
            }, timeoutDuration) as unknown as number;
        });

        observer.observe(observedElement, {childList: true, subtree: true});
    });
}

function isMouseoverMutation(mutationRecords: MutationRecord[]): boolean {
    for (const mutation of mutationRecords) {
        if (mutation.target instanceof HTMLElement) {
            const className = mutation.target.className;
            // Ignore mouseovers over the graph in index.py
            if (className == "graph" || className == "hover_menu") {
                return true;
            }
        }
    }
    return false;
}

export async function abortrepeat() {
    const db = await openDatabase();

    const transaction = db.transaction([repeatUrlsTable], "readwrite");
    const store = transaction.objectStore(repeatUrlsTable);

    const entry = await getRecord<repeatUrlsEntry>(store, currentUrl);
    if (entry) {
        entry.times = 0;
        await putRecord<repeatUrlsEntry>(store, entry);
    }
}

export async function repeat(
    times: number,
    prefix = "",
): Promise<repeatUrlsEntry> {
    const db = await openDatabase();

    const transaction = db.transaction([repeatUrlsTable], "readwrite");
    const store = transaction.objectStore(repeatUrlsTable);

    const entry: repeatUrlsEntry = {
        url: currentUrl,
        metricPrefix: prefix,
        times: times,
    };

    return await putRecord<repeatUrlsEntry>(store, entry);
}

export async function nukeDataFromOrbit() {
    console.warn("Nuking data: started");
    const db = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = db.transaction([metricsTable], "readwrite");
        const store = transaction.objectStore(metricsTable);

        const clearRequest = store.clear();
        clearRequest.onsuccess = onSuccess(resolve, () =>
            console.warn("Nuking data: done."),
        );
        clearRequest.onerror = onError(reject);
    });
}

export async function clearData() {
    console.warn("Clearing all data: started");
    const db = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = db.transaction([metricsTable], "readwrite");
        const store = transaction.objectStore(metricsTable);

        let deletedRows = 0;
        const cursorRequest = store.openCursor();
        cursorRequest.onsuccess = (event: Event) => {
            const request = event.target as IDBRequest<IDBCursorWithValue>;
            const cursor = request.result;
            if (cursor) {
                if (cursor.value.url === currentUrl) {
                    deletedRows += 1;
                    cursor.delete();
                }
                cursor.continue();
            } else {
                console.warn(
                    `Clearing all data: ${deletedRows} records deleted.`,
                );
                resolve(deletedRows);
            }
        };
        cursorRequest.onerror = onError(reject);
    });
}
