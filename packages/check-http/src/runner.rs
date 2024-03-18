// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::checking_types::CheckResult;
use crate::checks::{self, CheckParameters, RequestInformation};
use crate::http::{self, ClientConfig, RequestConfig};

pub async fn collect_checks(
    client_cfg: ClientConfig,
    request_cfg: RequestConfig,
    request_information: RequestInformation,
    check_params: CheckParameters,
) -> Vec<CheckResult> {
    let response = http::perform_request(client_cfg, request_cfg).await;
    checks::collect_response_checks(response, request_information, check_params)
}
