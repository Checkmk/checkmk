// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{self, CheckResult, Collection, Levels, MetricMetaData, OutputType, Real};
use time::Duration;
use typed_builder::TypedBuilder;

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config {
    response_time: Option<Levels<Duration>>,
}

pub fn check(response_time: Duration, config: Config) -> Collection {
    Collection::from(&mut vec![check_response_time(
        response_time,
        config.response_time,
    )
    .unwrap_or_default()
    .map(|x| Real::from(x.as_seconds_f64()))])
}

fn check_response_time(
    response_time: Duration,
    levels: Option<Levels<Duration>>,
) -> Option<CheckResult<Duration>> {
    levels.map(|levels| {
        check::check_levels(
            response_time,
            levels,
            OutputType::Notice(format!(
                "Response time: {} ms",
                response_time.whole_milliseconds()
            )),
            MetricMetaData::builder()
                .label("overall_response_time")
                .uom("s".parse().unwrap())
                .build(),
        )
    })
}
