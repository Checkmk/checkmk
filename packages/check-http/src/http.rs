// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result as AnyhowResult;
use bytes::Bytes;
use http::{HeaderMap, HeaderName, HeaderValue};
use reqwest::{
    header::{CONTENT_TYPE, USER_AGENT},
    Error as ReqwestError, Method, RequestBuilder, Result as ReqwestResult, StatusCode, Version,
};
use std::time::Duration;

use crate::connection::{apply_connection_settings, ConnectionConfig};

pub struct ClientConfig {
    pub url: String,
    pub method: Method,
    pub user_agent: Option<HeaderValue>,
    pub headers: Option<Vec<(HeaderName, HeaderValue)>>,
    pub timeout: Duration,
    pub auth_user: Option<String>,
    pub auth_pw: Option<String>,
    pub body: Option<String>,
    pub content_type: Option<HeaderValue>,
}

// TODO(au): This seems a bit misplaced.
// When doing the request with one entry point instead of two,
// this can go to ClientConfig (that could be named RequestConfig again),
// but this needs some preparation.
pub struct RequestConfig {
    pub without_body: bool,
}

pub struct ProcessedResponse {
    pub version: Version,
    pub status: StatusCode,
    pub headers: HeaderMap,
    pub body: Option<ReqwestResult<Bytes>>,
}

pub fn prepare_request(
    cfg: ClientConfig,
    conn_cfg: ConnectionConfig,
) -> AnyhowResult<RequestBuilder> {
    let mut headers = HeaderMap::new();
    if let Some(ua) = cfg.user_agent {
        headers.insert(USER_AGENT, ua);
    }
    if let Some(content_type) = cfg.content_type {
        headers.insert(CONTENT_TYPE, content_type);
    }
    if let Some(hds) = cfg.headers {
        headers.extend(hds);
    }

    let client = reqwest::Client::builder();
    let client = apply_connection_settings(conn_cfg, client);
    let client = client
        .timeout(cfg.timeout)
        .default_headers(headers)
        .build()?;

    let req = client.request(cfg.method, cfg.url);
    let req = if let Some(body) = cfg.body {
        req.body(body)
    } else {
        req
    };

    if let Some(user) = cfg.auth_user {
        Ok(req.basic_auth(user, cfg.auth_pw))
    } else {
        Ok(req)
    }
}

pub async fn perform_request(
    request: RequestBuilder,
    cfg: RequestConfig,
) -> Result<ProcessedResponse, ReqwestError> {
    let response = request.send().await?;

    let headers = response.headers().to_owned();
    let version = response.version();
    let status = response.status();
    let body = match cfg.without_body {
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
