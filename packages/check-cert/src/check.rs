// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::fmt::{Display, Formatter, Result as FormatResult};

#[derive(Debug, Clone, Copy)]
pub enum Real {
    Integer(isize),
    Double(f64),
}

impl From<isize> for Real {
    fn from(x: isize) -> Self {
        Real::Integer(x)
    }
}

impl From<f64> for Real {
    fn from(x: f64) -> Self {
        Real::Double(x)
    }
}

impl Display for Real {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        match self {
            Self::Integer(x) => write!(f, "{}", x),
            Self::Double(x) => write!(f, "{:.06}", x),
        }
    }
}

#[derive(Debug, PartialEq)]
pub struct Bounds<T> {
    pub min: T,
    pub max: T,
}

impl<T> Bounds<T> {
    pub fn map<F, U>(self, f: F) -> Bounds<U>
    where
        F: FnMut(T) -> U,
        U: Clone,
    {
        Bounds::from(&[self.min, self.max].map(f))
    }
}

impl<T> From<&[T; 2]> for Bounds<T>
where
    T: Clone,
{
    fn from(arr: &[T; 2]) -> Self {
        Self {
            min: arr[0].clone(),
            max: arr[1].clone(),
        }
    }
}

#[derive(Debug, PartialEq)]
pub struct Levels<T> {
    pub warn: T,
    pub crit: T,
}

impl<T> Levels<T> {
    pub fn map<F, U>(self, f: F) -> Levels<U>
    where
        F: FnMut(T) -> U,
        U: Clone,
    {
        Levels::from(&[self.warn, self.crit].map(f))
    }
}

impl<T> From<&[T; 2]> for Levels<T>
where
    T: Clone,
{
    fn from(arr: &[T; 2]) -> Self {
        Self {
            warn: arr[0].clone(),
            crit: arr[1].clone(),
        }
    }
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
    pub fn try_new(levels: Levels<T>) -> Result<Self, Box<dyn std::error::Error>> {
        if levels.warn >= levels.crit {
            Ok(Self { levels })
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
    pub fn try_new(levels: Levels<T>) -> Result<Self, Box<dyn std::error::Error>> {
        if levels.crit >= levels.warn {
            Ok(Self { levels })
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
    fn check(&self, value: &T, summary: String) -> SimpleCheckResult;
}

impl<T> LevelsCheck<T> for LowerLevels<T>
where
    T: PartialOrd,
{
    fn check(&self, value: &T, summary: String) -> SimpleCheckResult {
        SimpleCheckResult::new(self.evaluate(value), summary)
    }
}

impl<T> LevelsCheck<T> for UpperLevels<T>
where
    T: PartialOrd,
{
    fn check(&self, value: &T, summary: String) -> SimpleCheckResult {
        SimpleCheckResult::new(self.evaluate(value), summary)
    }
}

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
enum State {
    #[default]
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

#[derive(Debug, PartialEq)]
pub struct Metric<T> {
    label: String,
    value: T,
    uom: Option<String>,
    levels: Option<Levels<T>>,
    bounds: Option<Bounds<T>>,
}

impl<T> Metric<T>
where
    T: Display,
{
    pub fn builder(label: &str, value: T) -> MetricBuilder<T> {
        MetricBuilder::new(label, value)
    }
}

impl<T> Metric<T> {
    pub fn map<F, U>(self, mut f: F) -> Metric<U>
    where
        F: FnMut(T) -> U,
        F: Copy,
        U: Clone,
    {
        Metric {
            label: self.label,
            value: f(self.value),
            uom: self.uom,
            levels: self.levels.map(|v| v.map(f)),
            bounds: self.bounds.map(|v| v.map(f)),
        }
    }
}

impl<T> Display for Metric<T>
where
    T: Display,
{
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
pub struct MetricBuilder<T> {
    label: String,
    value: T,
    uom: Option<String>,
    levels: Option<Levels<T>>,
    bounds: Option<Bounds<T>>,
}

impl<T> MetricBuilder<T> {
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

#[derive(Debug, Default)]
pub struct Summary {
    state: State,
    text: String,
}

impl Summary {
    fn new(state: State, text: String) -> Self {
        Self { state, text }
    }
}

impl Display for Summary {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "{}{}",
            self.text,
            match self.state {
                State::Ok => "",
                State::Warn => " (!)",
                State::Crit => " (!!)",
                State::Unknown => " (?)",
            }
        )
    }
}

#[derive(Debug, Default)]
pub struct SimpleCheckResult {
    summary: Summary,
}

impl SimpleCheckResult {
    fn new(state: State, text: String) -> Self {
        Self {
            summary: Summary::new(state, text),
        }
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

pub struct CheckResult<T> {
    summary: Summary,
    #[allow(dead_code)]
    metrics: Option<Metric<T>>,
}

impl<T> CheckResult<T> {
    fn new(state: State, text: String, metrics: Option<Metric<T>>) -> Self {
        Self {
            summary: Summary::new(state, text),
            metrics,
        }
    }

    pub fn ok(summary: String, metrics: Metric<T>) -> Self {
        Self::new(State::Ok, summary, Some(metrics))
    }

    pub fn warn(summary: String, metrics: Metric<T>) -> Self {
        Self::new(State::Warn, summary, Some(metrics))
    }

    pub fn crit(summary: String, metrics: Metric<T>) -> Self {
        Self::new(State::Crit, summary, Some(metrics))
    }

    pub fn unknown(summary: String, metrics: Metric<T>) -> Self {
        Self::new(State::Unknown, summary, Some(metrics))
    }
}

impl From<SimpleCheckResult> for CheckResult<()> {
    fn from(x: SimpleCheckResult) -> Self {
        Self {
            summary: x.summary,
            metrics: None,
        }
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
        let out = Self::from(SimpleCheckResult::unknown(String::from(message)));
        eprintln!("{}", out);
        out.bye()
    }
}

impl Display for Writer {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        let mut out = format!("{}", self.state);
        if !self.summary.is_empty() {
            out = format!("{} - {}", out, self.summary);
        }
        write!(f, "{}", out)?;
        Ok(())
    }
}

impl From<SimpleCheckResult> for Writer {
    fn from(check_result: SimpleCheckResult) -> Self {
        Self {
            state: check_result.summary.state,
            summary: check_result.summary.to_string(),
        }
    }
}

impl From<Vec<CheckResult<()>>> for Writer {
    fn from(check_results: Vec<CheckResult<()>>) -> Self {
        Self {
            state: match check_results.iter().map(|cr| &cr.summary.state).max() {
                Some(state) => *state,
                None => State::Ok,
            },
            summary: check_results
                .iter()
                .map(|cr| &cr.summary)
                .filter(|s| !s.text.is_empty())
                .map(|s| s.to_string())
                .collect::<Vec<_>>()
                .join(", "),
        }
    }
}

#[cfg(test)]
mod test_metrics_map {
    use super::{Bounds, Levels, Metric};

    #[test]
    fn test_bounds() {
        assert_eq!(
            Bounds { min: 1, max: 10 }.map(&|v| v * 10),
            Bounds { min: 10, max: 100 }
        );
        assert_eq!(
            Bounds::from(&[1, 10]).map(&|v| v * 10),
            Bounds { min: 10, max: 100 }
        );
    }

    #[test]
    fn test_levels() {
        assert_eq!(
            Levels { warn: 1, crit: 10 }.map(&|v| v * 10),
            Levels {
                warn: 10,
                crit: 100
            }
        );
        assert_eq!(
            Levels::from(&[1, 10]).map(&|v| v * 10),
            Levels {
                warn: 10,
                crit: 100,
            }
        );
    }

    fn s(s: &str) -> String {
        String::from(s)
    }

    #[test]
    fn test_metric() {
        assert_eq!(
            Metric {
                label: s("Label"),
                value: 42,
                uom: Some(s("unit")),
                levels: Some(Levels { warn: 5, crit: 10 }),
                bounds: Some(Bounds { min: 1, max: 10 })
            }
            .map(|v| v * 10),
            Metric {
                label: s("Label"),
                value: 420,
                uom: Some(s("unit")),
                levels: Some(Levels {
                    warn: 50,
                    crit: 100,
                }),
                bounds: Some(Bounds { min: 10, max: 100 })
            }
        );
    }
}

#[cfg(test)]
mod test_metrics_display {
    use super::{Bounds, Levels, Metric, MetricBuilder, Real};

    #[test]
    fn test_default() {
        assert_eq!(
            format!(
                "{}",
                Metric::<Real>::builder("name", Real::Integer(42)).build()
            ),
            "name=42;;;;"
        );
        assert_eq!(
            format!(
                "{}",
                MetricBuilder::<Real>::new("name", Real::Integer(42)).build()
            ),
            "name=42;;;;"
        );
    }

    #[test]
    fn test_uom() {
        assert_eq!(
            format!(
                "{}",
                MetricBuilder::<Real>::new("name", Real::Integer(42))
                    .uom("ms")
                    .build()
            ),
            "name=42ms;;;;"
        );
    }

    #[test]
    fn test_levels() {
        assert_eq!(
            format!(
                "{}",
                MetricBuilder::<Real>::new("name", Real::Integer(42))
                    .levels(Levels {
                        warn: Real::Integer(24),
                        crit: Real::Integer(42)
                    })
                    .build()
            ),
            "name=42;24;42;;"
        );
    }

    #[test]
    fn test_chain_all_integer() {
        assert_eq!(
            format!(
                "{}",
                MetricBuilder::<Real>::new("name", Real::Integer(42))
                    .uom("ms")
                    .levels(Levels {
                        warn: Real::Integer(24),
                        crit: Real::Integer(42)
                    })
                    .bounds(Bounds {
                        min: Real::Integer(0),
                        max: Real::Integer(100)
                    })
                    .build()
            ),
            "name=42ms;24;42;0;100"
        );
    }

    #[test]
    fn test_chain_all_double() {
        assert_eq!(
            format!(
                "{}",
                MetricBuilder::<Real>::new("name", Real::Double(42.0))
                    .uom("ms")
                    .levels(Levels {
                        warn: Real::Double(24.0),
                        crit: Real::Double(42.0)
                    })
                    .bounds(Bounds {
                        min: Real::Double(0.0),
                        max: Real::Double(100.0)
                    })
                    .build()
            ),
            "name=42.000000ms;24.000000;42.000000;0.000000;100.000000"
        );
    }
}

#[cfg(test)]
mod test_writer_format {
    use super::{SimpleCheckResult, Writer};

    fn s(s: &str) -> String {
        String::from(s)
    }

    #[test]
    fn test_single_check_result_ok() {
        assert_eq!(
            format!("{}", Writer::from(SimpleCheckResult::ok(s("summary")))),
            "OK - summary"
        );
    }

    #[test]
    fn test_single_check_result_warn() {
        assert_eq!(
            format!("{}", Writer::from(SimpleCheckResult::warn(s("summary")))),
            "WARNING - summary (!)"
        );
    }

    #[test]
    fn test_single_check_result_crit() {
        assert_eq!(
            format!("{}", Writer::from(SimpleCheckResult::crit(s("summary")))),
            "CRITICAL - summary (!!)"
        );
    }

    #[test]
    fn test_single_check_result_unknown() {
        assert_eq!(
            format!("{}", Writer::from(SimpleCheckResult::unknown(s("summary")))),
            "UNKNOWN - summary (?)"
        );
    }

    #[test]
    fn test_no_check_results_is_ok() {
        assert_eq!(format!("{}", Writer::from(vec![])), "OK");
    }

    #[test]
    fn test_merge_check_results_with_state_only() {
        let cr1 = SimpleCheckResult::default();
        let cr2 = SimpleCheckResult::default();
        let cr3 = SimpleCheckResult::default();
        assert_eq!(
            format!("{}", Writer::from(vec![cr1.into(), cr2.into(), cr3.into()])),
            "OK"
        );
    }

    #[test]
    fn test_merge_check_results_ok() {
        let cr1 = SimpleCheckResult::ok(s("summary 1"));
        let cr2 = SimpleCheckResult::ok(s("summary 2"));
        let cr3 = SimpleCheckResult::ok(s("summary 3"));
        assert_eq!(
            format!("{}", Writer::from(vec![cr1.into(), cr2.into(), cr3.into()])),
            "OK - summary 1, summary 2, summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_warn() {
        let cr1 = SimpleCheckResult::ok(s("summary 1"));
        let cr2 = SimpleCheckResult::warn(s("summary 2"));
        let cr3 = SimpleCheckResult::ok(s("summary 3"));
        assert_eq!(
            format!("{}", Writer::from(vec![cr1.into(), cr2.into(), cr3.into()])),
            "WARNING - summary 1, summary 2 (!), summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_crit() {
        let cr1 = SimpleCheckResult::ok(s("summary 1"));
        let cr2 = SimpleCheckResult::warn(s("summary 2"));
        let cr3 = SimpleCheckResult::crit(s("summary 3"));
        assert_eq!(
            format!("{}", Writer::from(vec![cr1.into(), cr2.into(), cr3.into()])),
            "CRITICAL - summary 1, summary 2 (!), summary 3 (!!)"
        );
    }

    #[test]
    fn test_merge_check_results_unknown() {
        let cr1 = SimpleCheckResult::ok(s("summary 1"));
        let cr2 = SimpleCheckResult::warn(s("summary 2"));
        let cr3 = SimpleCheckResult::crit(s("summary 3"));
        let cr4 = SimpleCheckResult::unknown(s("summary 4"));
        assert_eq!(
            format!(
                "{}",
                Writer::from(vec![cr1.into(), cr2.into(), cr3.into(), cr4.into()])
            ),
            "UNKNOWN - summary 1, summary 2 (!), summary 3 (!!), summary 4 (?)"
        );
    }
}
