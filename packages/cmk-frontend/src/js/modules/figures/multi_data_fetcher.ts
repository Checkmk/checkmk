/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// Data update scheduler
// Receives one function pointer which is regularly called
// Supports scheduling modes
// - enable
// - disable
// - force_update
// - suspend_for (seconds)
// - update_if_older_than (seconds)
import {json} from "d3";

import type {CMKAjaxReponse} from "@/modules/types";
import {is_window_active} from "@/modules/utils";

export class Scheduler {
    _scheduled_function: () => void;
    _update_interval: number;
    _enabled: boolean;
    _last_update: number;
    _suspend_updates_until: number;

    constructor(scheduled_function: () => void, update_interval: number) {
        this._scheduled_function = scheduled_function;
        this._update_interval = update_interval;
        this._enabled = false;
        this._last_update = 0;
        this._suspend_updates_until = 0;
        setInterval(() => this._schedule(), 1000);
    }

    get_update_interval() {
        return this._update_interval;
    }

    set_update_interval(seconds: number) {
        this._update_interval = seconds;
    }

    enable() {
        this._enabled = true;
    }

    disable() {
        this._enabled = false;
    }

    suspend_for(seconds: number) {
        this._suspend_updates_until =
            Math.floor(new Date().getTime() / 1000) + seconds;
    }

    update_if_older_than(seconds: number) {
        const now = Math.floor(new Date().getTime() / 1000);
        if (now > this._last_update + seconds) {
            this._scheduled_function();
            const now = Math.floor(new Date().getTime() / 1000);
            this._last_update = now;
        }
    }

    force_update() {
        this._scheduled_function();
        this._last_update = Math.floor(new Date().getTime() / 1000);
    }

    _schedule() {
        if (!this._enabled) return;
        if (!is_window_active()) return;
        const now = Math.floor(new Date().getTime() / 1000);
        if (now < this._suspend_updates_until) return;
        // This function is called every second. Add 0.5 seconds grace time
        // for function which expect an update every second
        if (now + 0.5 > this._last_update + this._update_interval) {
            this._last_update = now;
            this._scheduled_function();
        }
    }
}

interface FetchOperationsBodyContent {
    interval: number;
    fetch_in_progress?: boolean;
    last_update?: number;
    active?: boolean;
}

type FetchHooksBodyContent = ((data?: any) => void)[];
// Allows scheduling of multiple url calls
// Registered hooks will be call on receiving data
export class MultiDataFetcher {
    scheduler: Scheduler;
    _fetch_operations: Record<
        string,
        Record<string, FetchOperationsBodyContent>
    >;
    _fetch_hooks: Record<string, Record<string, FetchHooksBodyContent>>;

    constructor() {
        this.scheduler = new Scheduler(() => this._schedule_operations(), 1);
        this._fetch_operations = {};
        this._fetch_hooks = {};
    }

    reset() {
        // Urls to call
        // {"url": {"body": {"interval": 10}}
        this._fetch_operations = {};

        // Hooks to call when receiving data
        // {"url": {"body": [funcA, funcB]}}
        this._fetch_hooks = {};
    }

    subscribe_hook(
        post_url: string,
        post_body: string,
        subscriber_func: (data?: any) => void,
    ) {
        // New url and body
        if (this._fetch_hooks[post_url] == undefined) {
            this._fetch_hooks[post_url] = {};
            this._fetch_hooks[post_url][post_body] = [subscriber_func];
            return;
        }
        // New body to existing url
        if (this._fetch_hooks[post_url][post_body] == undefined) {
            this._fetch_hooks[post_url][post_body] = [subscriber_func];
            return;
        }
        // Existing url and body
        this._fetch_hooks[post_url][post_body].push(subscriber_func);
    }

    add_fetch_operation(post_url: string, post_body: string, interval: number) {
        if (this._fetch_operations[post_url] == undefined)
            this._fetch_operations[post_url] = {};

        this._fetch_operations[post_url][post_body] =
            this._default_operation_options(interval);
    }

    _default_operation_options(interval: number) {
        return {
            active: true, // May be used to temporarily disable the operation
            last_update: 0, // Last time the fetch operation was sent (not received)
            fetch_in_progress: false,
            interval: interval,
        };
    }

    _schedule_operations() {
        if (!is_window_active()) return;
        for (const url_id in this._fetch_operations) {
            for (const body_id in this._fetch_operations[url_id]) {
                this._process_operation(url_id, body_id);
            }
        }
    }

    _process_operation(post_url: string, post_body: string) {
        const now = Math.floor(new Date().getTime() / 1000);

        const operation = this._fetch_operations[post_url][post_body];
        if (!operation.active || operation.fetch_in_progress) return;

        if (operation.last_update! + operation.interval > now) return;

        operation.last_update = now;
        operation.fetch_in_progress = true;
        this._fetch(post_url, post_body);
    }

    _fetch(post_url: string, post_body: string) {
        // TODO: improve error handling, d3js supports promises
        json(encodeURI(post_url), {
            credentials: "include",
            method: "POST",
            body: post_body,
            headers: {
                "Content-type": "application/x-www-form-urlencoded",
            },
        }).then(response => {
            this._fetch_callback(
                post_url,
                post_body,
                response as CMKAjaxReponse<{figure_response: any}>,
            );
        });
    }

    _fetch_callback(
        post_url: string,
        post_body: string,
        api_response: CMKAjaxReponse<{figure_response: any}>,
    ) {
        const response = api_response.result;
        const data = response.figure_response;

        const now = Math.floor(new Date().getTime() / 1000);

        if (
            this._fetch_operations[post_url] == undefined ||
            this._fetch_operations[post_url][post_body] == undefined
        )
            return;

        this._fetch_operations[post_url][post_body].last_update = now;
        this._fetch_operations[post_url][post_body].fetch_in_progress = false;

        // Inform subscribers
        this._fetch_hooks[post_url][post_body].forEach(
            (subscriber_func: (data: any) => void) => {
                subscriber_func(data);
            },
        );
    }
}
