/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {zxcvbn, zxcvbnOptions} from "@zxcvbn-ts/core";

const loadOptions = async () => {
    /** Lazy loading sizable dictionaries from zxcvbn, webpack relies
     * on the 'webpackChunkName: "/zxcvbn"' to create the chunk.
     * https://github.com/zxcvbn-ts/zxcvbn/blob/master/docs/guide/lazy-loading/README.md#lazy-loading
     */
    const {dictionary: commonDict, adjacencyGraphs} = await import(
        /* webpackChunkName: "/zxcvbn" */ "@zxcvbn-ts/language-common"
    );
    const {dictionary: enDict, translations} = await import(
        /* webpackChunkName: "/zxcvbn" */ "@zxcvbn-ts/language-en"
    );

    return {
        dictionary: {
            ...commonDict,
            ...enDict,
        },
        graphs: adjacencyGraphs,
        translations: translations,
    };
};

export async function initPasswordStrength() {
    // Mapping password strength score to data-* attributes sent
    // ... from the a backend
    window.addEventListener("load", async function () {
        // Find all elements with CSS class name 'new-password'
        const allMeters = document.querySelectorAll("meter.password_meter");
        if (allMeters.length == 0) return;

        const options = await loadOptions();
        zxcvbnOptions.setOptions(options);

        for (const meter of allMeters as NodeListOf<HTMLMeterElement>) {
            if (
                meter.parentElement === null ||
                meter.parentElement.parentElement === null
            ) {
                console.error(
                    "Found meter without a parentElement, skipping: ",
                    meter,
                );
                continue;
            }
            const passwordFieldList =
                meter.parentElement.parentElement.querySelectorAll(
                    "input[type=password]",
                ) as NodeListOf<HTMLInputElement>;
            if (passwordFieldList.length == 0) {
                console.error(
                    "Could not find the password field for the password meter!",
                    meter,
                );
                continue;
            }
            if (passwordFieldList.length > 1) {
                console.error(
                    "Found multiple password fields for the password meter!",
                    meter,
                );
                continue;
            }
            const passwordField = passwordFieldList[0];

            // add span for the text
            const passwordText = document.createElement("span");
            meter.parentElement.insertAdjacentElement("afterend", passwordText);

            passwordField.addEventListener("input", function () {
                const userInput = passwordField.value as string;
                if (userInput == "") {
                    passwordText.innerHTML = "";
                    meter.innerHTML = "";
                    meter.value = 0;
                    return;
                }
                const passwordStrength = zxcvbn(userInput);
                // Out meter handles 0 as no password
                const score = passwordStrength.score + 1;

                meter.value = score;

                // The strings are stored in the data attributes, since we currently have the
                // translations only on the backend...
                const score_string = meter.attributes.getNamedItem(
                    "data-password_strength_" + score.toString(),
                )!.value;
                /* eslint-disable no-unsanitized/property -- Highlight existing violations CMK-17846 */
                passwordText.innerHTML = score_string;
                meter.innerHTML = score_string;
                /* eslint-enable no-unsanitized/property */
            });
        }
    });
}
