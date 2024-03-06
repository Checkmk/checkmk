/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface CMKAjaxReponse<Result> {
    result_code: 0 | 1;
    result: Result;
    severity: "success" | "error";
}

export type PartialK<T, K extends PropertyKey = PropertyKey> = Partial<
    Pick<T, Extract<keyof T, K>>
> &
    Omit<T, K> extends infer O
    ? {[P in keyof O]: O[P]}
    : never;

export interface PlotDefinition {
    id: string;
    color: string;
    plot_type: string;
    label: string;
    use_tags: string[];
    hidden: boolean;
    is_scalar: boolean;
    metric?: {
        bounds: Record<string, number>;
        unit: Record<string, string>;
    };
}

export interface RequireConfirmation {
    html: string;
    confirmButtonText: string;
    cancelButtonText: string;
    customClass: {
        confirmButton: "confirm_question";
        icon: "confirm_icon confirm_question";
    };
}

declare global {
    interface JQueryStatic {
        //This is introduced for mobile.ts since it uses JQuery Mobile
        //However, Typescript doesn't recognize any mobile attribute in JQueryStatic
        //that's why I added it.
        mobile: any;
    }
}
