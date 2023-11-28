// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::mem;
use typed_builder::TypedBuilder;

#[derive(Debug, Clone)]
pub enum Real {
    Integer(isize),
    Double(f64),
}

impl Default for Real {
    fn default() -> Self {
        Self::Integer(isize::default())
    }
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

#[derive(Debug, PartialEq, Clone)]
pub struct Bounds<T>
where
    T: Clone,
{
    pub min: T,
    pub max: T,
}

impl<T> Bounds<T>
where
    T: Clone,
{
    pub fn map<F, U>(self, f: F) -> Bounds<U>
    where
        F: FnMut(T) -> U,
        U: Clone + Default,
    {
        Bounds::from(&mut [self.min, self.max].map(f))
    }
}

impl<T> From<&mut [T; 2]> for Bounds<T>
where
    T: Clone + Default,
{
    fn from(arr: &mut [T; 2]) -> Self {
        Self {
            min: mem::take(&mut arr[0]),
            max: mem::take(&mut arr[1]),
        }
    }
}

#[derive(Debug, PartialEq, Clone)]
pub struct Levels<T> {
    pub warn: T,
    pub crit: T,
}

impl<T> Levels<T>
where
    T: Clone,
{
    pub fn map<F, U>(self, f: F) -> Levels<U>
    where
        F: FnMut(T) -> U,
        U: Clone + Default,
    {
        Levels::from(&mut [self.warn, self.crit].map(f))
    }
}

impl<T> From<&mut [T; 2]> for Levels<T>
where
    T: Default,
{
    fn from(arr: &mut [T; 2]) -> Self {
        Self {
            warn: mem::take(&mut arr[0]),
            crit: mem::take(&mut arr[1]),
        }
    }
}

#[derive(Debug)]
pub enum LevelsStrategy {
    Upper,
    Lower,
}

impl LevelsStrategy {
    pub fn cmp<T: PartialOrd>(&self, x: &T, y: &T) -> bool {
        match self {
            Self::Upper => PartialOrd::ge(x, y),
            Self::Lower => PartialOrd::lt(x, y),
        }
    }
}

#[derive(Debug, TypedBuilder)]
pub struct LevelsCheckerArgs {
    label: String,
    #[builder(default, setter(transform = |x: &str| Some(x.to_string()) ))]
    uom: Option<String>,
}

#[derive(Debug)]
pub struct LevelsChecker<T> {
    pub strategy: LevelsStrategy,
    pub levels: Levels<T>,
}

impl<T> LevelsChecker<T>
where
    T: Clone + PartialOrd,
{
    pub fn try_new(
        strategy: LevelsStrategy,
        levels: Levels<T>,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        strategy
            .cmp(&levels.crit, &levels.warn)
            .then_some(Self { strategy, levels })
            .ok_or(Box::from("bad values"))
    }

    pub fn check(&self, value: T, summary: String, args: LevelsCheckerArgs) -> CheckResult<T> {
        let evaluate = |value: &T| -> State {
            if self.strategy.cmp(value, &self.levels.crit) {
                State::Crit
            } else if self.strategy.cmp(value, &self.levels.warn) {
                State::Warn
            } else {
                State::Ok
            }
        };
        let r = SimpleCheckResult::new(evaluate(&value), summary);
        CheckResult {
            summary: r.summary,
            metrics: Some(Metric::<T> {
                label: args.label,
                value,
                uom: args.uom,
                levels: Some(self.levels.clone()),
                bounds: None,
            }),
        }
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

#[derive(Debug, Default, PartialEq, Clone, TypedBuilder)]
pub struct Metric<T>
where
    T: Clone,
{
    label: String,
    value: T,
    #[builder(default, setter(transform = |x: &str| Some(x.to_string()) ))]
    uom: Option<String>,
    #[builder(default, setter(transform = |x: &Levels<T>| Some(x.clone()) ))]
    levels: Option<Levels<T>>,
    #[builder(default, setter(transform = |x: &Bounds<T>| Some(x.clone()) ))]
    bounds: Option<Bounds<T>>,
}

impl<T> Metric<T>
where
    T: Clone,
{
    pub fn map<F, U>(self, mut f: F) -> Metric<U>
    where
        F: FnMut(T) -> U,
        F: Copy,
        U: Clone + Default,
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
    T: Clone + Display,
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
}

pub struct CheckResult<T>
where
    T: Clone,
{
    summary: Summary,
    metrics: Option<Metric<T>>,
}

impl<T> CheckResult<T>
where
    T: Clone,
{
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

impl<T> CheckResult<T>
where
    T: Clone,
{
    pub fn map<F, U>(self, f: F) -> CheckResult<U>
    where
        F: FnMut(T) -> U,
        F: Copy,
        U: Clone + Default,
    {
        CheckResult {
            summary: self.summary,
            metrics: self.metrics.map(|m| m.map(f)),
        }
    }
}

impl<T> From<SimpleCheckResult> for CheckResult<T>
where
    T: Clone,
{
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
    metrics: String,
}

impl Writer {
    pub fn exit_code(&self) -> i32 {
        match self.state {
            State::Ok => 0,
            State::Warn => 1,
            State::Crit => 2,
            State::Unknown => 3,
        }
    }
}

impl Display for Writer {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        let mut out = format!("{}", self.state);
        if !self.summary.is_empty() {
            out = format!("{} - {}", out, self.summary);
        }
        if !self.metrics.is_empty() {
            out = format!("{} | {}", out, self.metrics);
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
            metrics: String::new(),
        }
    }
}

impl From<&Vec<CheckResult<Real>>> for Writer {
    fn from(check_results: &Vec<CheckResult<Real>>) -> Self {
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
            metrics: check_results
                .iter()
                .flat_map(|cr| &cr.metrics)
                .map(|s| s.to_string())
                .collect::<Vec<_>>()
                .join(", "),
        }
    }
}

pub fn bail_out(message: &str) -> ! {
    let out = Writer::from(SimpleCheckResult::unknown(String::from(message)));
    eprintln!("{}", out);
    std::process::exit(out.exit_code())
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
            Bounds::from(&mut [1, 10]).map(&|v| v * 10),
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
            Levels::from(&mut [1, 10]).map(&|v| v * 10),
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
    use super::{Bounds, Levels, Metric, Real};

    fn i(x: isize) -> Real {
        Real::Integer(x)
    }

    fn d(x: f64) -> Real {
        Real::Double(x)
    }

    #[test]
    fn test_default() {
        assert_eq!(
            format!(
                "{}",
                Metric::<Real>::builder()
                    .label("name".to_string())
                    .value(i(42))
                    .build()
            ),
            "name=42;;;;"
        );
    }

    #[test]
    fn test_uom() {
        assert_eq!(
            format!(
                "{}",
                Metric::<Real>::builder()
                    .label("name".to_string())
                    .value(i(42))
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
                Metric::<Real>::builder()
                    .label("name".to_string())
                    .value(i(42))
                    .levels(&Levels {
                        warn: i(24),
                        crit: i(42)
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
                Metric::<Real>::builder()
                    .label("name".to_string())
                    .value(i(42))
                    .uom("ms")
                    .levels(&Levels {
                        warn: i(24),
                        crit: i(42)
                    })
                    .bounds(&Bounds {
                        min: i(0),
                        max: i(100)
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
                Metric::<Real>::builder()
                    .label("name".to_string())
                    .value(d(42.0))
                    .uom("ms")
                    .levels(&Levels {
                        warn: d(24.0),
                        crit: d(42.0)
                    })
                    .bounds(&Bounds {
                        min: d(0.0),
                        max: d(100.0)
                    })
                    .build()
            ),
            "name=42.000000ms;24.000000;42.000000;0.000000;100.000000"
        );
    }
}

#[cfg(test)]
mod test_writer_format {
    use super::{CheckResult, Metric, Real, SimpleCheckResult, Writer};

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
        assert_eq!(format!("{}", Writer::from(&vec![])), "OK");
    }

    #[test]
    fn test_merge_check_results_with_state_only() {
        let cr1 = SimpleCheckResult::default();
        let cr2 = SimpleCheckResult::default();
        let cr3 = SimpleCheckResult::default();
        assert_eq!(
            format!(
                "{}",
                Writer::from(&vec![cr1.into(), cr2.into(), cr3.into()])
            ),
            "OK"
        );
    }

    #[test]
    fn test_merge_check_results_ok() {
        let cr1 = SimpleCheckResult::ok(s("summary 1"));
        let cr2 = SimpleCheckResult::ok(s("summary 2"));
        let cr3 = SimpleCheckResult::ok(s("summary 3"));
        assert_eq!(
            format!(
                "{}",
                Writer::from(&vec![cr1.into(), cr2.into(), cr3.into()])
            ),
            "OK - summary 1, summary 2, summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_warn() {
        let cr1 = SimpleCheckResult::ok(s("summary 1"));
        let cr2 = SimpleCheckResult::warn(s("summary 2"));
        let cr3 = SimpleCheckResult::ok(s("summary 3"));
        assert_eq!(
            format!(
                "{}",
                Writer::from(&vec![cr1.into(), cr2.into(), cr3.into()])
            ),
            "WARNING - summary 1, summary 2 (!), summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_crit() {
        let cr1 = SimpleCheckResult::ok(s("summary 1"));
        let cr2 = SimpleCheckResult::warn(s("summary 2"));
        let cr3 = SimpleCheckResult::crit(s("summary 3"));
        assert_eq!(
            format!(
                "{}",
                Writer::from(&vec![cr1.into(), cr2.into(), cr3.into()])
            ),
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
                Writer::from(&vec![cr1.into(), cr2.into(), cr3.into(), cr4.into()])
            ),
            "UNKNOWN - summary 1, summary 2 (!), summary 3 (!!), summary 4 (?)"
        );
    }

    fn m(name: &str, x: isize) -> Metric<Real> {
        Metric::<Real>::builder()
            .label(name.to_string())
            .value(Real::Integer(x))
            .build()
    }

    #[test]
    fn test_merge_check_results_with_metrics() {
        let cr1 = CheckResult::ok(s("summary 1"), m("m1", 13));
        let cr2 = CheckResult::warn(s("summary 2"), m("m2", 37));
        let cr3 = CheckResult::crit(s("summary 3"), m("m3", 42));
        assert_eq!(
            format!("{}", Writer::from(&vec![cr1, cr2, cr3])),
            "CRITICAL - summary 1, summary 2 (!), summary 3 (!!) | m1=13;;;;, m2=37;;;;, m3=42;;;;"
        );
    }
}
