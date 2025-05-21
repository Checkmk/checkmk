/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import "fake-indexeddb";

import {
    afterAll,
    beforeAll,
    beforeEach,
    describe,
    expect,
    jest,
    test,
} from "@jest/globals";

import {activate_tracking} from "@/modules/tracking";
import type {repeatUrlsEntry} from "@/modules/tracking_database";
import {
    getRecord,
    openDatabase,
    putRecord,
    repeatUrlsTable,
} from "@/modules/tracking_database";

async function getStore() {
    const db = await openDatabase();
    const transaction = db.transaction([repeatUrlsTable], "readwrite");
    return transaction.objectStore(repeatUrlsTable);
}

describe("When the indexeddb is empty", () => {
    const location = window.location;
    const warn = global.console.warn;

    beforeAll(() => {
        global.console.warn = jest.fn();

        delete (window as Partial<Window>).location;
        // @ts-ignore  (CMK-23761)
        window.location = {
            ...window.location,
            reload: jest.fn(),
        };
    });

    beforeEach(() => {
        (global.console.warn as jest.Mock).mockClear();
        (window.location.reload as jest.Mock).mockClear();
    });

    afterAll(() => {
        // @ts-ignore  (CMK-23761)
        window.location = location;
        global.console.warn = warn;
    });

    test("we want to reload the page 5 times", async () => {
        const store = await getStore();
        const entry: repeatUrlsEntry = {
            url: "localhost",
            metricPrefix: "",
            times: 5,
        };
        await putRecord(store, entry);
        const storedEntry = await getRecord<repeatUrlsEntry>(
            store,
            "localhost",
        );
        expect(storedEntry).not.toBeNull();
        expect(storedEntry?.url).toBe("localhost");
        expect(storedEntry?.times).toBe(5);
        expect(window.location.reload).not.toHaveBeenCalled();
    });

    // This will take 2 seconds due to the setTimeout() call in it.
    test("activate_tracking will trigger a reload (5 times)", async () => {
        await activate_tracking("localhost", 100, 50);
        expect(window.location.reload).toHaveBeenCalled();
        expect(console.warn).toBeCalled();
        // Check decrement.
        const store = await getStore();
        const storedEntry = await getRecord<repeatUrlsEntry>(
            store,
            "localhost",
        );
        expect(storedEntry).not.toBeNull();
        expect(storedEntry?.url).toBe("localhost");
        expect(storedEntry?.times).toBe(4);
    });
});
