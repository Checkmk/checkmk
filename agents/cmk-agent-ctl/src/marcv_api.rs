// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::certs;
use crate::config::ServerSpec;
use reqwest;
use serde::Deserialize;
use std::error::Error;

#[derive(Deserialize)]
struct JSONResponse {
    message: String,
}

pub fn register(_server_address: &str, _csr: Vec<u8>) -> reqwest::Result<Vec<u8>> {
    return Ok(Vec::from(
        "-----BEGIN CERTIFICATE-----\ndummy\n-----END CERTIFICATE-----\n",
    ));
}

pub fn agent_data(
    monitoring_data: Vec<u8>,
    server_spec: ServerSpec,
) -> Result<String, Box<dyn Error>> {
    let client_chain = server_spec.client_chain.into_bytes();
    let uuid = server_spec.uuid;
    let marcv_address = server_spec.marcv_address;

    // TODO: Use root cert from TOFU
    Ok(certs::client(Some(client_chain), None)?
        .post(marcv_address + "/agent-data")
        .multipart(
            reqwest::blocking::multipart::Form::new()
                .text("uuid", uuid)
                .part(
                    "upload_file",
                    reqwest::blocking::multipart::Part::bytes(monitoring_data)
                        // Note: We need to set the file name, otherwise the request won't have the
                        // right format. However, the value itself does not matter.
                        .file_name("agent_data"),
                ),
        )
        .send()?
        .json::<JSONResponse>()?
        .message)
}
