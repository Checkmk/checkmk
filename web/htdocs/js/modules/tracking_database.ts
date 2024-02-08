/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

const repeatUrlsTable = "repeatUrls";
const metricsTable = "metrics";

type metricsEntry = {
    loadTime: number;
    metricName: string;
    url: string;
    recordCreated: number;
};

type repeatUrlsEntry = {
    url: string;
    metricPrefix: string;
    times: number;
};

// We use a database!
function openDatabase(): Promise<IDBDatabase> {
    const dbName = "PageMetricsDB";

    // put the date in when you made schema changes
    const dbVersion = 20240119;

    return new Promise((resolve, reject) => {
        const openRequest = indexedDB.open(dbName, dbVersion);

        openRequest.onupgradeneeded = (event: Event) => {
            const request = event.target as IDBRequest<IDBDatabase>;
            const db = request.result;
            // drop and recreate
            if (db.objectStoreNames.contains(metricsTable)) {
                db.deleteObjectStore(metricsTable);
            }
            if (!db.objectStoreNames.contains(metricsTable)) {
                const objectStore = db.createObjectStore(metricsTable, {
                    autoIncrement: true,
                });
                objectStore.createIndex("url", "url", {unique: false});
                objectStore.createIndex("metricName", "metricName", {
                    unique: false,
                });
                objectStore.createIndex("recordCreated", "recordCreated", {
                    unique: false,
                });
            }
            // drop and recreate
            if (db.objectStoreNames.contains(repeatUrlsTable)) {
                db.deleteObjectStore(repeatUrlsTable);
            }
            if (!db.objectStoreNames.contains(repeatUrlsTable)) {
                db.createObjectStore(repeatUrlsTable, {
                    keyPath: "url",
                });
            }
        };

        openRequest.onsuccess = onSuccess<IDBDatabase>(resolve);
        openRequest.onerror = onError<IDBDatabase>(reject);
    });
}

function addRecord<T>(store: IDBObjectStore, object: T): Promise<T> {
    return new Promise((resolve, reject) => {
        const addRequest = store.add(object);

        addRequest.onsuccess = onSuccess<T>(resolve);
        addRequest.onerror = onError<T>(reject);
    });
}

function putRecord<T>(store: IDBObjectStore, object: T): Promise<T> {
    return new Promise((resolve, reject) => {
        const putRequest = store.put(object);

        putRequest.onsuccess = onSuccess<T>(resolve);
        putRequest.onerror = onError<T>(reject);
    });
}

function getRecord<T>(store: IDBObjectStore, key: string): Promise<T | null> {
    return new Promise((resolve, reject) => {
        const getRequest = store.get(key);

        getRequest.onsuccess = onSuccess<T>(resolve);
        getRequest.onerror = onError<T>(reject);
    });
}

// Generic resolve and reject functions for promises.
function onSuccess<T>(resolve: (value: T) => void, callback?: () => void) {
    return (event: Event) => {
        const request = event.target as IDBRequest<T>;
        resolve(request.result);
        if (callback) callback();
    };
}

function onError<T>(reject: (reason?: any) => void, callback?: () => void) {
    return (event: Event) => {
        const request = event.target as IDBRequest<T>;
        reject(request.error);
        if (callback) callback();
    };
}

export {
    addRecord,
    getRecord,
    metricsEntry,
    metricsTable,
    onError,
    onSuccess,
    openDatabase,
    putRecord,
    repeatUrlsEntry,
    repeatUrlsTable,
};
