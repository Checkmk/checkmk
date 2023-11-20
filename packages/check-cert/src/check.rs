// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::fmt::{Display, Formatter, Result as FormatResult};

#[derive(Debug)]
pub struct Bounds<T> {
    pub min: T,
    pub max: T,
}

#[derive(Debug)]
pub struct Levels<T> {
    pub warn: T,
    pub crit: T,
}

#[derive(Debug)]
pub struct LowerLevels<T> {
    pub levels: Levels<T>,
}

#[derive(Debug)]
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

    fn evaluate(&self, value: &T) -> State {
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

    fn evaluate(&self, value: &T) -> State {
        if value >= &self.levels.crit {
            State::Crit
        } else if value >= &self.levels.warn {
            State::Warn
        } else {
            State::Ok
        }
    }
}

pub trait LevelsCheck<T> {
    fn check(&self, value: &T, summary: String) -> CheckResult;
}

impl<T: PartialOrd> LevelsCheck<T> for LowerLevels<T> {
    fn check(&self, value: &T, summary: String) -> CheckResult {
        CheckResult::new(self.evaluate(value), summary)
    }
}

impl<T: PartialOrd> LevelsCheck<T> for UpperLevels<T> {
    fn check(&self, value: &T, summary: String) -> CheckResult {
        CheckResult::new(self.evaluate(value), summary)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
enum State {
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

#[derive(Debug)]
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

#[derive(Debug)]
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

#[derive(Debug)]
pub struct CheckResult {
    state: State,
    summary: String,
}

impl CheckResult {
    fn new(state: State, summary: String) -> Self {
        Self { state, summary }
    }

    pub fn ok(summary: String) -> Self {
        Self::new(State::Ok, summary)
    }

    pub fn warn(summary: String) -> Self {
        Self::new(State::Warn, summary)
    }

    pub fn crit(summary: String) -> Self {
        Self::new(State::Crit, summary)
    }

    pub fn unknown(summary: String) -> Self {
        Self::new(State::Unknown, summary)
    }

    pub fn from_levels<T>(levels: &impl LevelsCheck<T>, value: &T, summary: String) -> Self {
        levels.check(value, summary)
    }
}

impl Default for CheckResult {
    fn default() -> Self {
        Self::new(State::Ok, String::from(""))
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

#[derive(Debug)]
pub struct Writer {
    state: State,
    summary: String,
}

impl Writer {
    pub fn bye(&self) -> ! {
        std::process::exit(match self.state {
            State::Ok => 0,
            State::Warn => 1,
            State::Crit => 2,
            State::Unknown => 3,
        })
    }

    pub fn bail_out(message: &str) -> ! {
        let out = Self::from(CheckResult::unknown(String::from(message)));
        eprintln!("{}", out);
        out.bye()
    }
}

impl Display for Writer {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        if self.summary.is_empty() {
            write!(f, "{}", self.state)?;
        } else {
            write!(f, "{} - {}", self.state, self.summary)?;
        }
        Ok(())
    }
}

impl From<CheckResult> for Writer {
    fn from(check_result: CheckResult) -> Self {
        Self {
            state: check_result.state,
            summary: check_result.summary,
        }
    }
}

impl From<Vec<CheckResult>> for Writer {
    fn from(check_results: Vec<CheckResult>) -> Self {
        Self {
            state: match check_results.iter().map(|cr| &cr.state).max() {
                Some(state) => state.clone(),
                None => State::Ok,
            },
            summary: check_results
                .iter()
                .filter(|cr| !cr.summary.is_empty())
                .map(|cr| cr.to_string())
                .collect::<Vec<_>>()
                .join(", "),
        }
    }
}

#[cfg(test)]
mod test_metrics_display {
    use super::{Bounds, Levels, Metric, MetricBuilder};

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
        assert_eq!(
            format!(
                "{}",
                MetricBuilder::<u32>::new("name", 42)
                    .uom("ms")
                    .levels(Levels { warn: 24, crit: 42 })
                    .bounds(Bounds { min: 0, max: 100 })
                    .build()
            ),
            "name=42ms;24;42;0;100"
        );
    }
}

#[cfg(test)]
mod test_writer_format {
    use super::{CheckResult, Writer};

    fn s(s: &str) -> String {
        String::from(s)
    }

    #[test]
    fn test_no_check_results_is_ok() {
        assert_eq!(format!("{}", Writer::from(vec![])), "OK");
    }

    #[test]
    fn test_merge_check_results_with_state_only() {
        let cr1 = CheckResult::default();
        let cr2 = CheckResult::default();
        let cr3 = CheckResult::default();
        assert_eq!(format!("{}", Writer::from(vec![cr1, cr2, cr3])), "OK");
    }

    #[test]
    fn test_merge_check_results_ok() {
        let cr1 = CheckResult::ok(s("summary 1"));
        let cr2 = CheckResult::ok(s("summary 2"));
        let cr3 = CheckResult::ok(s("summary 3"));
        assert_eq!(
            format!("{}", Writer::from(vec![cr1, cr2, cr3])),
            "OK - summary 1, summary 2, summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_warn() {
        let cr1 = CheckResult::ok(s("summary 1"));
        let cr2 = CheckResult::warn(s("summary 2"));
        let cr3 = CheckResult::ok(s("summary 3"));
        assert_eq!(
            format!("{}", Writer::from(vec![cr1, cr2, cr3])),
            "WARNING - summary 1, summary 2 (!), summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_crit() {
        let cr1 = CheckResult::ok(s("summary 1"));
        let cr2 = CheckResult::warn(s("summary 2"));
        let cr3 = CheckResult::crit(s("summary 3"));
        assert_eq!(
            format!("{}", Writer::from(vec![cr1, cr2, cr3])),
            "CRITICAL - summary 1, summary 2 (!), summary 3 (!!)"
        );
    }

    #[test]
    fn test_merge_check_results_unknown() {
        let cr1 = CheckResult::ok(s("summary 1"));
        let cr2 = CheckResult::warn(s("summary 2"));
        let cr3 = CheckResult::crit(s("summary 3"));
        let cr4 = CheckResult::unknown(s("summary 4"));
        assert_eq!(
            format!("{}", Writer::from(vec![cr1, cr2, cr3, cr4])),
            "UNKNOWN - summary 1, summary 2 (!), summary 3 (!!), summary 4 (?)"
        );
    }
}
