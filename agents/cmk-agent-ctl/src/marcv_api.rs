// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::certs;
use crate::config::ServerSpec;
use reqwest;
use serde::{Deserialize, Serialize};
use std::error::Error;

#[derive(Deserialize)]
struct JSONResponse {
    message: String,
}

#[derive(Serialize)]
struct CSRBody {
    csr: String,
}

#[derive(Deserialize)]
struct CSRResponse {
    cert: String,
}

pub fn register(
    server_address: &str,
    root_cert: &str,
    csr: String,
    checkmk_user: &str,
    checkmk_password: &str,
) -> Result<String, Box<dyn Error>> {
    Ok(
        certs::client(None, Some(String::from(root_cert).into_bytes()))?
            .post(format!("https://{}/csr", server_address))
            .header(
                "authentication",
                format!("Bearer {} {}", checkmk_user, checkmk_password),
            )
            .json(&CSRBody { csr: csr })
            .send()?
            .json::<CSRResponse>()?
            .cert,
    )
}

pub fn agent_data(
    uuid: &str,
    marcv_address: &str,
    server_spec: &ServerSpec,
    monitoring_data: Vec<u8>,
) -> Result<String, Box<dyn Error>> {
    let client_chain = String::from(&server_spec.client_chain).into_bytes();

    // TODO: Use root cert from TOFU
    Ok(certs::client(Some(client_chain), None)?
        .post(String::from(marcv_address) + "/agent-data")
        .multipart(
            reqwest::blocking::multipart::Form::new()
                .text("uuid", String::from(uuid))
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
