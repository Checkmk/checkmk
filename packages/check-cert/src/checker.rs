// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::fmt::{Display, Formatter, Result as FormatResult};
use time::Duration;
use x509_parser::time::ASN1Time;
use x509_parser::x509::X509Name;

pub struct Bounds<T> {
    pub min: T,
    pub max: T,
}

pub struct Levels<T> {
    pub warn: T,
    pub crit: T,
}

pub struct LowerLevels<T> {
    pub levels: Levels<T>,
}

pub struct UpperLevels<T> {
    pub levels: Levels<T>,
}

impl<T> LowerLevels<T>
where
    T: PartialOrd,
{
    pub fn try_new(warn: T, crit: T) -> Result<Self, Box<dyn std::error::Error>> {
        if warn >= crit {
            Ok(Self {
                levels: Levels { warn, crit },
            })
        } else {
            Err(Box::from("bad values"))
        }
    }

    pub fn evaluate(&self, value: &T) -> State {
        if value < &self.levels.crit {
            State::Crit
        } else if value < &self.levels.warn {
            State::Warn
        } else {
            State::Ok
        }
    }
}

impl<T> UpperLevels<T>
where
    T: PartialOrd,
{
    pub fn try_new(warn: T, crit: T) -> Result<Self, Box<dyn std::error::Error>> {
        if crit >= warn {
            Ok(Self {
                levels: Levels { warn, crit },
            })
        } else {
            Err(Box::from("bad values"))
        }
    }

    pub fn evaluate(&self, value: &T) -> State {
        if value >= &self.levels.crit {
            State::Crit
        } else if value >= &self.levels.warn {
            State::Warn
        } else {
            State::Ok
        }
    }
}

#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub enum State {
    Ok,
    Warn,
    Crit,
    Unknown,
}

impl Display for State {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        match self {
            Self::Ok => write!(f, "OK"),
            Self::Warn => write!(f, "WARNING"),
            Self::Crit => write!(f, "CRITICAL"),
            Self::Unknown => write!(f, "UNKNOWN"),
        }
    }
}

pub struct Metric<T>
where
    // hack to bound T to numeric values
    T: Into<f64>,
{
    label: String,
    value: T,
    uom: Option<String>,
    levels: Option<Levels<T>>,
    bounds: Option<Bounds<T>>,
}

impl<T: Into<f64> + Default + Display> Metric<T> {
    pub fn builder(label: &str, value: T) -> MetricBuilder<T> {
        MetricBuilder::new(label, value)
    }
}

impl<T: Into<f64> + Display> Display for Metric<T> {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        write!(
            f,
            "{}={}{};{};{};{};{}",
            self.label,
            self.value,
            self.uom.clone().unwrap_or_default(),
            self.levels
                .as_ref()
                .map_or(String::new(), |v| v.warn.to_string()),
            self.levels
                .as_ref()
                .map_or(String::new(), |v| v.crit.to_string()),
            self.bounds
                .as_ref()
                .map_or(String::new(), |v| v.min.to_string()),
            self.bounds
                .as_ref()
                .map_or(String::new(), |v| v.max.to_string()),
        )
    }
}

pub struct MetricBuilder<T: Into<f64>> {
    label: String,
    value: T,
    uom: Option<String>,
    levels: Option<Levels<T>>,
    bounds: Option<Bounds<T>>,
}

impl<T: Into<f64>> MetricBuilder<T> {
    pub fn new(label: &str, value: T) -> Self {
        Self {
            label: label.to_string(),
            value,
            uom: None,
            levels: None,
            bounds: None,
        }
    }

    pub fn uom(mut self, uom: &str) -> Self {
        self.uom = Some(uom.to_string());
        self
    }

    pub fn levels(mut self, levels: Levels<T>) -> Self {
        self.levels = Some(levels);
        self
    }

    pub fn bounds(mut self, bounds: Bounds<T>) -> Self {
        self.bounds = Some(bounds);
        self
    }

    pub fn build(self) -> Metric<T> {
        Metric {
            label: self.label,
            value: self.value,
            uom: self.uom,
            levels: self.levels,
            bounds: self.bounds,
        }
    }
}

pub struct CheckResult {
    pub state: State,
    pub summary: String,
}

impl CheckResult {
    pub fn new(state: State, summary: String) -> Self {
        Self { state, summary }
    }

    pub fn ok(summary: String) -> Self {
        Self {
            state: State::Ok,
            summary,
        }
    }

    pub fn warn(summary: String) -> Self {
        Self {
            state: State::Warn,
            summary,
        }
    }

    pub fn crit(summary: String) -> Self {
        Self {
            state: State::Crit,
            summary,
        }
    }

    pub fn unknown(summary: String) -> Self {
        Self {
            state: State::Unknown,
            summary,
        }
    }
}

impl Default for CheckResult {
    fn default() -> Self {
        Self {
            state: State::Ok,
            summary: String::from(""),
        }
    }
}

impl Display for CheckResult {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "{}{}",
            self.summary,
            match self.state {
                State::Ok => "",
                State::Warn => " (!)",
                State::Crit => " (!!)",
                State::Unknown => " (?)",
            }
        )
    }
}

pub fn check_details_serial(serial: String, expected: Option<String>) -> Option<CheckResult> {
    match expected {
        None => None,
        Some(expected) => {
            if serial == expected {
                Some(CheckResult::ok(format!("Serial {}", serial)))
            } else {
                Some(CheckResult::warn(format!(
                    "Serial is {} but expected {}",
                    serial, expected
                )))
            }
        }
    }
}

pub fn check_details_subject(subject: &X509Name, expected: Option<String>) -> Option<CheckResult> {
    match expected {
        None => None,
        Some(expected) => {
            let subject = subject.to_string();
            // subject string has the form: `CN=domain`
            if subject == expected {
                Some(CheckResult::ok(subject.to_string()))
            } else {
                Some(CheckResult::warn(format!(
                    "Subject is {} but expected {}",
                    subject, expected
                )))
            }
        }
    }
}

pub fn check_details_issuer(issuer: &X509Name, expected: Option<String>) -> Option<CheckResult> {
    match expected {
        None => None,
        Some(expected) => {
            let issuer = issuer.to_string();

            if issuer == expected {
                Some(CheckResult::ok(format!("Issuer {}", issuer)))
            } else {
                Some(CheckResult::warn(format!(
                    "Issuer is {} but expected {}",
                    issuer, expected
                )))
            }
        }
    }
}

pub fn check_response_time(response_time: Duration, levels: UpperLevels<Duration>) -> CheckResult {
    CheckResult::new(
        levels.evaluate(&response_time),
        format!(
            "Certificate obtained in {} ms",
            response_time.whole_milliseconds()
        ),
    )
}

pub fn check_validity_not_after(
    time_to_expiration: Option<Duration>,
    levels: LowerLevels<Duration>,
    not_after: ASN1Time,
) -> CheckResult {
    match time_to_expiration {
        None => CheckResult::crit(format!("Certificate expired ({})", not_after)),
        Some(time_to_expiration) => CheckResult::new(
            levels.evaluate(&time_to_expiration),
            format!(
                "Certificate expires in {} day(s) ({})",
                time_to_expiration.whole_days(),
                not_after
            ),
        ),
    }
}

#[cfg(test)]
mod test_metrics_display {
    use super::{Levels, Metric, MetricBuilder};

    #[test]
    fn test_default() {
        assert_eq!(
            format!("{}", Metric::<u32>::builder("name", 42).build()),
            "name=42;;;;"
        );
        assert_eq!(
            format!("{}", MetricBuilder::<u32>::new("name", 42).build()),
            "name=42;;;;"
        );
    }

    #[test]
    fn test_uom() {
        assert_eq!(
            format!(
                "{}",
                MetricBuilder::<u32>::new("name", 42).uom("ms").build()
            ),
            "name=42ms;;;;"
        );
    }

    #[test]
    fn test_levels() {
        assert_eq!(
            format!(
                "{}",
                MetricBuilder::<u32>::new("name", 42)
                    .levels(Levels { warn: 24, crit: 42 })
                    .build()
            ),
            "name=42;24;42;;"
        );
    }

    #[test]
    fn test_chain_all() {
        // We have no Bounds implementation, yet
        assert_eq!(
            format!(
                "{}",
                MetricBuilder::<u32>::new("name", 42)
                    .uom("ms")
                    .levels(Levels { warn: 24, crit: 42 })
                    .build()
            ),
            "name=42ms;24;42;;"
        );
    }
}
