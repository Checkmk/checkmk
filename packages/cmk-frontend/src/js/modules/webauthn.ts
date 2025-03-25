/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {add_class, remove_class} from "./utils";

function urlsafe_base64_decode(base64str: string): string {
    return window.atob(base64str.replace(/_/g, "/").replace(/-/g, "+"));
}

interface JsonEncodedCredential {
    type: string;
    id: string;
}

function parseCreationOptionsFromJSON(
    credentialcreationoptions: any,
): CredentialCreationOptions {
    /* The data comes from the server now as JSON, but the browser API likes
     * native types like Uint8Arrays... There is a draft for the 3rd spec to
     * include a function like this wo the API. Once we're there we can remove
     * this...*/
    const options = credentialcreationoptions["publicKey"];
    return {
        publicKey: {
            challenge: Uint8Array.from(
                urlsafe_base64_decode(options["challenge"]),
                c => c.charCodeAt(0),
            ),
            rp: options["rp"],
            user: {
                id: Uint8Array.from(
                    urlsafe_base64_decode(options["user"]["id"]),
                    c => c.charCodeAt(0),
                ),
                name: options["user"]["name"],
                displayName: options["user"]["displayName"],
            },
            pubKeyCredParams: options["pubKeyCredParams"],
            authenticatorSelection: options["authenticatorSelection"],
            excludeCredentials: options["excludeCredentials"].map(
                (e: JsonEncodedCredential) => ({
                    type: e["type"],
                    id: Uint8Array.from(urlsafe_base64_decode(e["id"]), c =>
                        c.charCodeAt(0),
                    ),
                }),
            ),
        },
    };
}

function parseRequestOptionsFromJSON(data: any): CredentialRequestOptions {
    const options = data["publicKey"];
    return {
        publicKey: {
            challenge: Uint8Array.from(
                urlsafe_base64_decode(options["challenge"]),
                c => c.charCodeAt(0),
            ),
            allowCredentials: options["allowCredentials"].map(
                (e: JsonEncodedCredential) => ({
                    type: e["type"],
                    id: Uint8Array.from(urlsafe_base64_decode(e["id"]), c =>
                        c.charCodeAt(0),
                    ),
                }),
            ),
        },
    };
}

export function register() {
    fetch("user_webauthn_register_begin.py", {
        method: "POST",
    })
        .then(function (response) {
            if (response.ok) {
                show_info("Activate your authenticator device now");
                return response.json();
            }
            throw new Error("Error getting registration data!");
        })
        .then(function (options) {
            if (!("credentials" in navigator)) {
                throw new DOMException(
                    "navigator does not have credentials property, probably no https?",
                    "SecurityError",
                );
            }
            return navigator.credentials.create(
                parseCreationOptionsFromJSON(options),
            );
        })
        .then(function (attestation) {
            const attestationPkc = attestation as PublicKeyCredential;
            const attestationPkcResponse =
                attestationPkc.response as AuthenticatorAttestationResponse;
            return fetch("user_webauthn_register_complete.py", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    attestationObject: btoa(
                        String.fromCharCode(
                            ...new Uint8Array(
                                attestationPkcResponse.attestationObject,
                            ),
                        ),
                    ),
                    clientDataJSON: btoa(
                        String.fromCharCode(
                            ...new Uint8Array(
                                attestationPkcResponse.clientDataJSON,
                            ),
                        ),
                    ),
                }),
            });
        })
        .then(function (response) {
            if (response.ok) {
                show_info("Registration successful");
                response.text().then(function (text) {
                    if (JSON.parse(text).replicate) {
                        if (JSON.parse(text).redirect) {
                            window.location.href =
                                "user_profile_replicate.py?back=index.py";
                        } else {
                            window.location.href =
                                "user_profile_replicate.py?back=user_two_factor_overview.py";
                        }
                        window.location.href =
                            "user_profile_replicate.py?back=user_two_factor_overview.py";
                    } else if (JSON.parse(text).redirect) {
                        window.location.href = "index.py";
                    } else {
                        window.location.href = "user_two_factor_overview.py";
                    }
                });
                show_info("Registration successful");
            } else {
                response.text().then(function (text) {
                    show_error(
                        "Registration failed (" +
                            text +
                            "). A Checkmk administrator may have a look at " +
                            "<tt>var/log/web.log</tt> to get additional information.",
                    );
                });
            }
        })
        .catch(function (e) {
            console.log(e.name, e);
            if (e.name == "SecurityError") {
                show_error(
                    "Can not enable two-factor authentication. You have to use HTTPS and access " +
                        "the GUI through a valid domain name (See #13325 for further information).",
                );
            } else if (e.name == "AbortError") {
                show_error(
                    "Registration failed - possible reasons are: <ul>" +
                        "<li>You have aborted the registration</li>" +
                        "<li>Your browser does not support the WebAuthn standard</li>" +
                        "<li>The browser configuration has disabled WebAuthn</li></ul>",
                );
            } else if (e.name == "InvalidStateError") {
                show_error(
                    "Registration failed: The given authenticator is not usable. This may " +
                        "be due to the repeated use of an already registered authenticator.",
                );
            } else {
                show_error("Registration failed: " + e.message);
            }
        });
}

function show_info(text: string) {
    show_message(text, "success");
}

function show_error(text: string) {
    show_message(text, "error");
}

function show_message(text: string, cls: string) {
    const msg = document.getElementById("webauthn_message")!;
    remove_class(msg, "error");
    remove_class(msg, "success");
    add_class(msg, cls);

    /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
    msg.innerHTML = text;
}

export function login() {
    fetch("user_webauthn_login_begin.py", {
        method: "POST",
    })
        .then(function (response) {
            if (response.ok) {
                show_info("Activate your authenticator device now");
                return response.json();
            }
            throw new Error("No credential available to authenticate!");
        })
        .then(function (options) {
            if (!("credentials" in navigator)) {
                throw new DOMException(
                    "navigator does not have credentials property, probably no https?",
                    "SecurityError",
                );
            }
            return navigator.credentials.get(
                parseRequestOptionsFromJSON(options),
            );
        })
        .then(function (assertion) {
            const assertionPkc = assertion as PublicKeyCredential;
            const assertionResponse =
                assertionPkc.response as AuthenticatorAssertionResponse;
            return fetch("user_webauthn_login_complete.py", {
                method: "POST",
                body: JSON.stringify({
                    credentialId: btoa(
                        String.fromCharCode(
                            ...new Uint8Array(assertionPkc.rawId),
                        ),
                    ),
                    authenticatorData: btoa(
                        String.fromCharCode(
                            ...new Uint8Array(
                                assertionResponse.authenticatorData,
                            ),
                        ),
                    ),
                    clientDataJSON: btoa(
                        String.fromCharCode(
                            ...new Uint8Array(assertionResponse.clientDataJSON),
                        ),
                    ),
                    signature: btoa(
                        String.fromCharCode(
                            ...new Uint8Array(assertionResponse.signature),
                        ),
                    ),
                }),
            });
        })
        .then(function (response) {
            if (response.ok) {
                show_info("Login successful");
            } else {
                show_error("Login failed.");
            }
        })
        .then(function () {
            window.location.href = "index.py";
        })
        .catch(function (e) {
            console.log(e);
            if (e.name == "SecurityError") {
                show_error("2FA not possible (See #13325 for details)");
            } else {
                show_error("WebAuthn login failed");
            }
        });
}
