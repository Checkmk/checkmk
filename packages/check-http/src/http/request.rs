// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use bytes::Bytes;
use http::{HeaderMap, HeaderName, HeaderValue, Method};
use reqwest::{
    header::CONTENT_TYPE, Client, RequestBuilder, Result as ReqwestResult, StatusCode, Version,
};

pub async fn send(client: Client, cfg: RequestConfig) -> ReqwestResult<ProcessedResponse> {
    let fetch_body = !cfg.without_body;

    let response = prepare_request(client, cfg).send().await?;

    let headers = response.headers().to_owned();
    let version = response.version();
    let status = response.status();
    let body = if fetch_body {
        Some(response.bytes().await)
    } else {
        None
    };

    Ok(ProcessedResponse {
        version,
        status,
        headers,
        body,
    })
}

pub struct RequestConfig {
    pub url: String,
    pub method: Method,
    pub headers: Option<Vec<(HeaderName, HeaderValue)>>,
    pub body: Option<String>,
    pub content_type: Option<HeaderValue>,
    pub auth_user: Option<String>,
    pub auth_pw: Option<String>,
    pub without_body: bool,
}

pub struct ProcessedResponse {
    pub version: Version,
    pub status: StatusCode,
    pub headers: HeaderMap,
    pub body: Option<ReqwestResult<Bytes>>,
}

fn prepare_request(client: Client, request_cfg: RequestConfig) -> RequestBuilder {
    let mut headers = HeaderMap::new();
    if let Some(content_type) = request_cfg.content_type {
        headers.insert(CONTENT_TYPE, content_type);
    }

    let req = client
        .request(request_cfg.method, request_cfg.url)
        .headers(headers);

    let req = if let Some(body) = request_cfg.body {
        req.body(body)
    } else {
        req
    };

    if let Some(user) = request_cfg.auth_user {
        req.basic_auth(user, request_cfg.auth_pw)
    } else {
        req
    }
}
