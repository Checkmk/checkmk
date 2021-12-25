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
            return fetch("user_webauthn_register_complete.py", {
                method: "POST",
                headers: {"Content-Type": "application/cbor"},
                body: CBOR.encode({
                    attestationObject: new Uint8Array(attestation.response.attestationObject),
                    clientDataJSON: new Uint8Array(attestation.response.clientDataJSON),
                }),
            });
        })
        .then(function (response) {
            if (response.ok) {
                show_info("Registration successful");
            } else {
                show_error(
                    "Registration failed. A Checkmk administrator may have a look at " +
                        "<tt>var/log/web.log</tt> to get additional information."
                );
            }
        })
        .then(function () {
            window.location = "user_two_factor_overview.py";
        })
        .catch(function (e) {
            console.log(e);
            if (e.name == "SecurityError") {
                show_error(
                    "Can not enable two-factor authentication. You have to use HTTPS and access " +
                        "the GUI thourgh a valid domain name (See #13325 for further information)."
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
    var msg = document.getElementById("webauthn_message");
    utils.remove_class(msg, "error");
    utils.remove_class(msg, "success");
    utils.add_class(msg, cls);

    msg.innerHTML = text;
}
