// Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import {CBOR} from "cbor_ext";
import * as utils from "utils";

export function register() {
    fetch("user_webauthn_register_begin.py", {
        method: "POST",
    })
        .then(function (response) {
            if (response.ok) {
                show_info("Activate your authenticator device now");
                return response.arrayBuffer();
            }
            throw new Error("Error getting registration data!");
        })
        .then(CBOR.decode)
        .then(function (options) {
            return navigator.credentials.create(options);
        })
        .then(function (attestation) {
            var attestationPkc = attestation as PublicKeyCredential;
            var attestationPkcResponse =
                attestationPkc.response as AuthenticatorAttestationResponse;
            return fetch("user_webauthn_register_complete.py", {
                method: "POST",
                headers: {"Content-Type": "application/cbor"},
                body: CBOR.encode({
                    attestationObject: new Uint8Array(attestationPkcResponse.attestationObject),
                    clientDataJSON: new Uint8Array(attestationPkcResponse.clientDataJSON),
                }),
            });
        })
        .then(function (response) {
            if (response.ok) {
                show_info("Registration successful");
                window.location.href = "user_two_factor_overview.py";
            } else {
                response.text().then(function (text) {
                    show_error(
                        "Registration failed (" +
                            text +
                            "). A Checkmk administrator may have a look at " +
                            "<tt>var/log/web.log</tt> to get additional information."
                    );
                });
            }
        })
        .catch(function (e) {
            console.log(e.name, e);
            if (e.name == "SecurityError") {
                show_error(
                    "Can not enable two-factor authentication. You have to use HTTPS and access " +
                        "the GUI thourgh a valid domain name (See #13325 for further information)."
                );
            } else if (e.name == "AbortError") {
                show_error(
                    "Registration failed - possible reasons are: <ul>" +
                        "<li>You have aborted the registration</li>" +
                        "<li>Your browser does not support the WebAuthn standard</li>" +
                        "<li>The browser configuration has disabled WebAuthn</li></ul>"
                );
            } else if (e.name == "InvalidStateError") {
                show_error(
                    "Registration failed: The given authenticator is not usable. This may " +
                        "be due to the repeated use of an already registered authenticator."
                );
            } else {
                show_error("Registration failed: " + e.message);
            }
        });
}

function show_info(text) {
    show_message(text, "success");
}

function show_error(text) {
    show_message(text, "error");
}

function show_message(text, cls) {
    var msg = document.getElementById("webauthn_message")!;
    utils.remove_class(msg, "error");
    utils.remove_class(msg, "success");
    utils.add_class(msg, cls);

    msg.innerHTML = text;
}

export function login() {
    fetch("user_webauthn_login_begin.py", {
        method: "POST",
    })
        .then(function (response) {
            if (response.ok) {
                show_info("Activate your authenticator device now");
                return response.arrayBuffer();
            }
            throw new Error("No credential available to authenticate!");
        })
        .then(CBOR.decode)
        .then(function (options) {
            return navigator.credentials.get(options);
        })
        .then(function (assertion) {
            var assertionPkc = assertion as PublicKeyCredential;
            var assertionResponse =
                assertionPkc.response as AuthenticatorAssertionResponse;
            return fetch("user_webauthn_login_complete.py", {
                method: "POST",
                headers: {"Content-Type": "application/cbor"},
                body: CBOR.encode({
                    credentialId: new Uint8Array(assertionPkc.rawId),
                    authenticatorData: new Uint8Array(assertionResponse.authenticatorData),
                    clientDataJSON: new Uint8Array(assertionResponse.clientDataJSON),
                    signature: new Uint8Array(assertionResponse.signature),
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
