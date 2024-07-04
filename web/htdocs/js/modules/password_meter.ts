import {zxcvbn, zxcvbnOptions} from "@zxcvbn-ts/core";
import * as zxcvbnCommonPackage from "@zxcvbn-ts/language-common";
import * as zxcvbnEnPackage from "@zxcvbn-ts/language-en";

export async function initPasswordStrength() {
    // Mapping password strength score to data-* attributes sent
    // ... from the a backend
    window.addEventListener("load", async function () {
        // Find all elements with CSS class name 'new-password'
        const allMeters = document.querySelectorAll("meter.password_meter");
        if (allMeters.length == 0) return;

        zxcvbnOptions.setOptions({
            dictionary: {
                ...zxcvbnCommonPackage.dictionary,
                ...zxcvbnEnPackage.dictionary,
            },
            graphs: zxcvbnCommonPackage.adjacencyGraphs,
            translations: zxcvbnEnPackage.translations,
        });

        for (const meter of allMeters as NodeListOf<HTMLMeterElement>) {
            if (
                meter.parentElement === null ||
                meter.parentElement.parentElement === null
            ) {
                console.error(
                    "Found meter without a parentElement, skipping: ",
                    meter
                );
                continue;
            }
            const passwordFieldList =
                meter.parentElement.parentElement.querySelectorAll(
                    "input[type=password]"
                ) as NodeListOf<HTMLInputElement>;
            if (passwordFieldList.length == 0) {
                console.error(
                    "Could not find the password field for the password meter!",
                    meter
                );
                continue;
            }
            if (passwordFieldList.length > 1) {
                console.error(
                    "Found multiple password fields for the password meter!",
                    meter
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
                const score_string =
                    meter.attributes[
                        "data-password_strength_" + score.toString()
                    ].value;
                passwordText.innerHTML = score_string;
                meter.innerHTML = score_string;
            });
        }
    });
}
