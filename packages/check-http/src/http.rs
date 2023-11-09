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

use crate::redirect::{self, ConnectionConfig, ForceIP};

pub struct RequestConfig {
    pub url: String,
    pub method: Method,
    pub user_agent: Option<HeaderValue>,
    pub headers: Option<Vec<(HeaderName, HeaderValue)>>,
    pub timeout: Duration,
    pub auth_user: Option<String>,
    pub auth_pw: Option<String>,
}

pub struct ProcessedResponse {
    pub version: Version,
    pub status: StatusCode,
    pub headers: HeaderMap,
    pub body: Option<ReqwestResult<Bytes>>,
}

pub fn prepare_request(
    cfg: RequestConfig,
    redir_cfg: ConnectionConfig,
) -> AnyhowResult<RequestBuilder> {
    let mut headers = HeaderMap::new();
    if let Some(ua) = cfg.user_agent {
        headers.insert(USER_AGENT, ua);
    }
    if let Some(hds) = cfg.headers {
        headers.extend(hds);
    }

    let client = reqwest::Client::builder();

    let client = match &redir_cfg.force_ip {
        None => client,
        Some(ipv) => match ipv {
            ForceIP::Ipv4 => client.local_address(IpAddr::V4(Ipv4Addr::UNSPECIFIED)),
            ForceIP::Ipv6 => client.local_address(IpAddr::V6(Ipv6Addr::UNSPECIFIED)),
        },
    };

    let redirect_policy = redirect::get_policy(redir_cfg);
    let client = client
        .redirect(redirect_policy)
        .timeout(cfg.timeout)
        .default_headers(headers)
        .build()?;

    let req = client.request(cfg.method, cfg.url);
    if let Some(user) = cfg.auth_user {
        Ok(req.basic_auth(user, cfg.auth_pw))
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
