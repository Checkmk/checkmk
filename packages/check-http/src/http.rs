// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result as AnyhowResult;
use bytes::Bytes;
use http::{HeaderMap, HeaderName, HeaderValue};
use reqwest::{
    header::USER_AGENT, Error as ReqwestError, Method, RequestBuilder, Result as ReqwestResult,
    StatusCode, Version,
};
use std::{
    net::{IpAddr, Ipv4Addr, Ipv6Addr},
    time::Duration,
};

use crate::redirect;
use crate::redirect::{ForceIP, OnRedirect};

pub struct ProcessedResponse {
    pub version: Version,
    pub status: StatusCode,
    pub headers: HeaderMap, // TODO(au): use
    pub body: Option<ReqwestResult<Bytes>>,
}

#[allow(clippy::too_many_arguments)] //TODO(au): Fix - Introduce separate configs/options for each function
pub fn prepare_request(
    url: String,
    method: Method,
    user_agent: Option<HeaderValue>,
    headers: Option<Vec<(HeaderName, HeaderValue)>>,
    timeout: Duration,
    auth_user: Option<String>,
    auth_pw: Option<String>,
    onredirect: OnRedirect,
    max_redirs: usize,
    force_ip: Option<ForceIP>,
) -> AnyhowResult<RequestBuilder> {
    let mut cli_headers = HeaderMap::new();
    if let Some(ua) = user_agent {
        cli_headers.insert(USER_AGENT, ua);
    }
    if let Some(hds) = headers {
        cli_headers.extend(hds);
    }

    let redirect_policy = redirect::get_policy(onredirect, force_ip.clone(), max_redirs);
    let client = reqwest::Client::builder();

    let client = match force_ip {
        None => client,
        Some(ipv) => match ipv {
            ForceIP::Ipv4 => client.local_address(IpAddr::V4(Ipv4Addr::UNSPECIFIED)),
            ForceIP::Ipv6 => client.local_address(IpAddr::V6(Ipv6Addr::UNSPECIFIED)),
        },
    };

    let client = client
        .redirect(redirect_policy)
        .timeout(timeout)
        .default_headers(cli_headers)
        .build()?;

    let req = client.request(method, url);
    if let Some(user) = auth_user {
        Ok(req.basic_auth(user, auth_pw))
    } else {
        Ok(req)
    }
}

pub async fn perform_request(
    request: RequestBuilder,
    without_body: bool,
) -> Result<ProcessedResponse, ReqwestError> {
    let response = request.send().await?;

    let headers = response.headers().to_owned();
    let version = response.version();
    let status = response.status();
    let body = match without_body {
        false => Some(response.bytes().await),
        true => None,
    };

    Ok(ProcessedResponse {
        version,
        status,
        headers,
        body,
    })
}
