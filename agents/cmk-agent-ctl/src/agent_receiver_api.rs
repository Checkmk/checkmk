// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::certs;
use http::StatusCode;
use reqwest;
use serde::{Deserialize, Serialize};
use std::error::Error;

#[derive(Deserialize)]
struct JSONResponse {
    message: String,
}

#[derive(Serialize)]
struct PairingBody {
    csr: String,
}

#[derive(Deserialize)]
struct PairingResponse {
    cert: String,
}

#[derive(Serialize)]
struct RegistrationWithHNBody {
    uuid: String,
    host_name: String,
}

pub fn pairing(
    server_address: &str,
    root_cert: &str,
    csr: String,
    credentials: &str,
) -> Result<String, Box<dyn Error>> {
    Ok(certs::client(Some(String::from(root_cert).into_bytes()))?
        .post(format!("https://{}/pairing", server_address))
        .header("authentication", format!("Bearer {}", credentials))
        .json(&PairingBody { csr })
        .send()?
        .json::<PairingResponse>()?
        .cert)
}

pub fn register_with_hostname(
    server_address: &str,
    root_cert: &str,
    credentials: &str,
    uuid: &str,
    host_name: &str,
) -> Result<(), Box<dyn Error>> {
    let response = certs::client(Some(String::from(root_cert).into_bytes()))?
        .post(format!("https://{}/register_with_hostname", server_address))
        .header("authentication", format!("Bearer {}", credentials))
        .json(&RegistrationWithHNBody {
            uuid: String::from(uuid),
            host_name: String::from(host_name),
        })
        .send()?;
    match response.status() {
        StatusCode::NO_CONTENT => Ok(()),
        _ => Err(response.text()?)?,
    }
}

// .header(
//     "client-cert",
//     base64::encode_config(
//         tls_server::certificate(&mut String::from(client_cert).as_bytes())?.0,
//         base64::URL_SAFE,
//     ),

pub fn agent_data(
    agent_receiver_address: &str,
    uuid: &str,
    monitoring_data: &Vec<u8>,
) -> Result<String, Box<dyn Error>> {
    // TODO:
    // - Send client cert in header
    // - Use root cert
    Ok(certs::client(None)?
        .post(String::from(agent_receiver_address) + "/agent-data")
        .multipart(
            reqwest::blocking::multipart::Form::new()
                .text("uuid", String::from(uuid))
                .part(
                    "upload_file",
                    reqwest::blocking::multipart::Part::bytes(monitoring_data.to_owned())
                        // Note: We need to set the file name, otherwise the request won't have the
                        // right format. However, the value itself does not matter.
                        .file_name("agent_data"),
                ),
        )
        .send()?
        .json::<JSONResponse>()?
        .message)
}
