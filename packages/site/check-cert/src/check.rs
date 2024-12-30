// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::mem;
use std::str::FromStr;
use typed_builder::TypedBuilder;

#[derive(Debug, Clone)]
#[cfg_attr(test, derive(PartialEq, PartialOrd))]
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

#[derive(Debug, Clone)]
#[cfg_attr(test, derive(PartialEq))]
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

#[derive(Debug, Clone)]
#[cfg_attr(test, derive(PartialEq))]
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

#[derive(Debug, Clone)]
#[cfg_attr(test, derive(PartialEq))]
pub struct Levels<T> {
    strategy: LevelsStrategy,
    warn: T,
    crit: T,
}

impl<T> Display for Levels<T>
where
    T: Display,
{
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        write!(
            f,
            "{}",
            match self.strategy {
                LevelsStrategy::Upper => format!("warn/crit at {}/{}", self.warn, self.crit),
                LevelsStrategy::Lower => format!("warn/crit below {}/{}", self.warn, self.crit),
            }
        )
    }
}

impl<T> Levels<T>
where
    T: Clone + PartialOrd,
{
    pub fn try_new(
        strategy: LevelsStrategy,
        warn: T,
        crit: T,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        strategy
            .cmp(&crit, &warn)
            .then_some(Self {
                strategy,
                warn,
                crit,
            })
            .ok_or(Box::from("bad values"))
    }

    pub fn map<F, U>(self, f: F) -> Levels<U>
    where
        F: FnMut(T) -> U,
        U: Clone + Default,
    {
        let arr = &mut [self.warn, self.crit].map(f);
        Levels {
            strategy: self.strategy,
            warn: mem::take(&mut arr[0]),
            crit: mem::take(&mut arr[1]),
        }
    }

    fn evaluate(&self, value: &T) -> State {
        if self.strategy.cmp(value, &self.crit) {
            State::Crit
        } else if self.strategy.cmp(value, &self.warn) {
            State::Warn
        } else {
            State::Ok
        }
    }
}

#[derive(Debug, Default, Clone, PartialEq)]
pub struct Uom(String);

impl FromStr for Uom {
    type Err = ();
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(Self(s.to_string()))
    }
}

impl Display for Uom {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        self.0.fmt(f)
    }
}

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
enum State {
    // See also: https://docs.checkmk.com/latest/en/devel_check_plugins.html
    #[default]
    Ok,
    Warn,
    Unknown,
    Crit,
}

impl State {
    fn as_str(&self) -> &'static str {
        match self {
            Self::Ok => "OK",
            Self::Warn => "WARNING",
            Self::Crit => "CRITICAL",
            Self::Unknown => "UNKNOWN",
        }
    }

    fn as_sym(&self) -> Option<&'static str> {
        match self {
            State::Ok => None,
            State::Warn => Some("!"),
            State::Crit => Some("!!"),
            State::Unknown => Some("?"),
        }
    }
}

#[derive(Debug, Default, Clone, TypedBuilder)]
#[cfg_attr(test, derive(PartialEq))]
pub struct Metric<T>
where
    T: Clone,
{
    #[builder(setter(transform = |x: impl Into<String>| x.into() ))]
    label: String,
    value: T,
    #[builder(default, setter(strip_option))]
    uom: Option<Uom>,
    #[builder(default)]
    levels: Option<Levels<T>>,
    #[builder(default)]
    bounds: Option<Bounds<T>>,
}

impl<T> Metric<T>
where
    T: Clone + PartialOrd,
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
            self.uom
                .as_ref()
                .map_or(Default::default(), ToString::to_string),
            self.levels
                .as_ref()
                .map_or(Default::default(), |v| v.warn.to_string()),
            self.levels
                .as_ref()
                .map_or(Default::default(), |v| v.crit.to_string()),
            self.bounds
                .as_ref()
                .map_or(Default::default(), |v| v.min.to_string()),
            self.bounds
                .as_ref()
                .map_or(Default::default(), |v| v.max.to_string()),
        )
    }
}

#[derive(Debug, Default)]
#[cfg_attr(test, derive(PartialEq))]
pub struct SimpleCheckResult {
    state: State,
    summary: Option<String>,
    details: Option<String>,
}

fn as_option(s: impl Into<String>) -> Option<String> {
    let s = s.into();
    (!s.is_empty()).then_some(s)
}

impl SimpleCheckResult {
    fn new(state: State, summary: Option<String>, details: Option<String>) -> Self {
        Self {
            state,
            summary,
            details,
        }
    }

    pub fn notice(notice: impl Into<String>) -> Self {
        Self::new(State::Ok, None, as_option(notice))
    }

    pub fn ok(summary: impl Into<String>) -> Self {
        Self::new(State::Ok, as_option(summary), None)
    }

    pub fn warn(summary: impl Into<String>) -> Self {
        Self::new(State::Warn, as_option(summary), None)
    }

    pub fn crit(summary: impl Into<String>) -> Self {
        Self::new(State::Crit, as_option(summary), None)
    }

    pub fn unknown(summary: impl Into<String>) -> Self {
        Self::new(State::Unknown, as_option(summary), None)
    }

    pub fn ok_with_details(summary: impl Into<String>, details: impl Into<String>) -> Self {
        Self::new(State::Ok, as_option(summary), as_option(details))
    }

    pub fn warn_with_details(summary: impl Into<String>, details: impl Into<String>) -> Self {
        Self::new(State::Warn, as_option(summary), as_option(details))
    }

    pub fn crit_with_details(summary: impl Into<String>, details: impl Into<String>) -> Self {
        Self::new(State::Crit, as_option(summary), as_option(details))
    }
}

pub struct CheckResult<T>
where
    T: Clone,
{
    state: State,
    summary: Option<String>,
    details: Option<String>,
    metrics: Option<Metric<T>>,
}

impl<T> Default for CheckResult<T>
where
    T: Clone,
{
    fn default() -> Self {
        SimpleCheckResult::default().into()
    }
}

impl<T> CheckResult<T>
where
    T: Clone + PartialOrd,
{
    fn new(
        state: State,
        summary: Option<String>,
        details: Option<String>,
        metrics: Option<Metric<T>>,
    ) -> Self {
        Self {
            state,
            summary,
            details,
            metrics,
        }
    }

    pub fn notice(notice: impl Into<String>, metrics: Metric<T>) -> Self {
        Self::new(State::Ok, None, as_option(notice), Some(metrics))
    }

    pub fn ok(summary: impl Into<String>, metrics: Metric<T>) -> Self {
        Self::new(State::Ok, as_option(summary), None, Some(metrics))
    }

    pub fn warn(summary: impl Into<String>, metrics: Metric<T>) -> Self {
        Self::new(State::Warn, as_option(summary), None, Some(metrics))
    }

    pub fn crit(summary: impl Into<String>, metrics: Metric<T>) -> Self {
        Self::new(State::Crit, as_option(summary), None, Some(metrics))
    }

    pub fn unknown(summary: impl Into<String>, metrics: Metric<T>) -> Self {
        Self::new(State::Unknown, as_option(summary), None, Some(metrics))
    }

    pub fn notice_from_levels(notice: impl Into<String>, metrics: Metric<T>) -> Self {
        let state = metrics
            .levels
            .as_ref()
            .map_or(State::Unknown, |levels| levels.evaluate(&metrics.value));
        match state {
            State::Ok => Self::notice(notice, metrics),
            _ => Self::new(state, as_option(notice), None, Some(metrics)),
        }
    }

    pub fn from_levels(summary: impl Into<String>, metrics: Metric<T>) -> Self {
        Self::new(
            metrics
                .levels
                .as_ref()
                .map_or(State::Unknown, |levels| levels.evaluate(&metrics.value)),
            as_option(summary),
            None,
            Some(metrics),
        )
    }

    pub fn ok_with_details(
        summary: impl Into<String>,
        details: impl Into<String>,
        metrics: Metric<T>,
    ) -> Self {
        Self::new(
            State::Ok,
            as_option(summary),
            as_option(details),
            Some(metrics),
        )
    }

    pub fn warn_with_details(
        summary: impl Into<String>,
        details: impl Into<String>,
        metrics: Metric<T>,
    ) -> Self {
        Self::new(
            State::Warn,
            as_option(summary),
            as_option(details),
            Some(metrics),
        )
    }

    pub fn crit_with_details(
        summary: impl Into<String>,
        details: impl Into<String>,
        metrics: Metric<T>,
    ) -> Self {
        Self::new(
            State::Crit,
            as_option(summary),
            as_option(details),
            Some(metrics),
        )
    }

    pub fn from_levels_with_details(
        summary: impl Into<String>,
        details: impl Into<String>,
        metrics: Metric<T>,
    ) -> Self {
        Self::new(
            metrics
                .levels
                .as_ref()
                .map_or(State::Unknown, |levels| levels.evaluate(&metrics.value)),
            as_option(summary),
            as_option(details),
            Some(metrics),
        )
    }
}

impl<T> CheckResult<T>
where
    T: Clone + PartialOrd,
{
    pub fn map<F, U>(self, f: F) -> CheckResult<U>
    where
        F: FnMut(T) -> U,
        F: Copy,
        U: Clone + Default,
    {
        CheckResult {
            state: self.state,
            summary: self.summary,
            details: self.details,
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
            state: x.state,
            summary: x.summary,
            details: x.details,
            metrics: None,
        }
    }
}

#[derive(Debug)]
enum CheckView {
    Text(State, String),
    TextLevels(State, String, Levels<Real>),
}

impl CheckView {
    fn new(state: State, text: &str, levels: Option<Levels<Real>>) -> Self {
        match levels {
            None => CheckView::Text(state, text.to_string()),
            Some(levels) => CheckView::TextLevels(state, text.to_string(), levels),
        }
    }
}

impl Display for CheckView {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        match self {
            Self::Text(state, text) => match state.as_sym() {
                None => write!(f, "{}", text),
                Some(sym) => write!(f, "{} ({})", text, sym),
            },
            Self::TextLevels(state, text, levels) => match state.as_sym() {
                None => write!(f, "{} ({})", text, levels),
                Some(sym) => write!(f, "{} ({}) ({})", text, levels, sym),
            },
        }
    }
}

#[derive(Debug, Default)]
pub struct Collection {
    state: State,
    summary: Vec<CheckView>,
    details: Vec<CheckView>,
    metrics: Vec<Metric<Real>>,
}

impl Collection {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add(&mut self, cr: CheckResult<Real>) {
        self.state = std::cmp::max(self.state, cr.state);
        if let Some(ref summary) = cr.summary {
            self.summary.push(match cr.metrics {
                None => CheckView::new(cr.state, summary, None),
                Some(ref metrics) => CheckView::new(cr.state, summary, metrics.levels.clone()),
            })
        }
        if let Some(ref details) = cr.details.or(cr.summary) {
            self.details.push(match cr.metrics {
                None => CheckView::new(cr.state, details, None),
                Some(ref metrics) => CheckView::new(cr.state, details, metrics.levels.clone()),
            })
        }
        if let Some(ref metrics) = cr.metrics {
            self.metrics.push(metrics.clone())
        }
    }

    pub fn join(&mut self, other: &mut Self) {
        self.state = std::cmp::max(self.state, other.state);
        self.summary.append(&mut other.summary);
        self.details.append(&mut other.details);
        self.metrics.append(&mut other.metrics);
    }
}

impl Display for Collection {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        let summary = self
            .summary
            .iter()
            .map(ToString::to_string)
            .collect::<Vec<_>>()
            .join(", ");
        let mut out = if summary.is_empty() {
            String::from(self.state.as_str())
        } else {
            // No SERVICE STATUS, this deviates from the Nagios guidelines
            // but follows our internal requirements.
            summary.to_string()
        };
        if !self.metrics.is_empty() {
            out = format!(
                "{} | {}",
                out,
                self.metrics
                    .iter()
                    .map(ToString::to_string)
                    .collect::<Vec<_>>()
                    .join(" ")
            );
        }
        if !self.details.is_empty() {
            out = format!(
                "{}\n{}",
                out,
                self.details
                    .iter()
                    .map(ToString::to_string)
                    .collect::<Vec<_>>()
                    .join("\n")
            );
        }
        write!(f, "{}", out)?;
        Ok(())
    }
}

impl From<SimpleCheckResult> for Collection {
    fn from(check_result: SimpleCheckResult) -> Self {
        let mut out = Collection::new();
        out.add(check_result.into());
        out
    }
}

impl From<&mut Vec<CheckResult<Real>>> for Collection {
    fn from(check_results: &mut Vec<CheckResult<Real>>) -> Self {
        check_results
            .drain(..)
            .fold(Collection::default(), |mut out, cr| {
                out.add(cr);
                out
            })
    }
}

pub fn exit_code(collection: &Collection) -> i32 {
    match collection.state {
        State::Ok => 0,
        State::Warn => 1,
        State::Crit => 2,
        State::Unknown => 3,
    }
}

pub fn bail_out(message: impl Into<String>) -> ! {
    let out = Collection::from(SimpleCheckResult::unknown(message));
    println!("{}", out);
    std::process::exit(exit_code(&out))
}

pub fn abort(message: impl Into<String>) -> ! {
    let out = Collection::from(SimpleCheckResult::crit(message));
    println!("{}", out);
    std::process::exit(exit_code(&out))
}

#[cfg(test)]
mod test_metrics_map {
    use super::{Bounds, Levels, LevelsStrategy, Metric, Uom};

    fn u(x: &str) -> Uom {
        x.parse().unwrap()
    }

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
            Levels::try_new(LevelsStrategy::Upper, 1, 10)
                .unwrap()
                .map(&|v| v * 10),
            Levels::try_new(LevelsStrategy::Upper, 10, 100).unwrap()
        );
    }

    #[test]
    fn test_metric() {
        assert_eq!(
            Metric::builder()
                .label("Label")
                .value(42)
                .uom(u("unit"))
                .levels(Levels::try_new(LevelsStrategy::Upper, 5, 10).ok())
                .bounds(Some(Bounds { min: 1, max: 10 }))
                .build()
                .map(|v| v * 10),
            Metric::builder()
                .label("Label")
                .value(420)
                .uom(u("unit"))
                .levels(Levels::try_new(LevelsStrategy::Upper, 50, 100).ok())
                .bounds(Some(Bounds { min: 10, max: 100 }))
                .build()
        );
    }
}

#[cfg(test)]
mod test_metrics_display {
    use super::{Bounds, Levels, LevelsStrategy, Metric, Real, Uom};

    fn i(x: isize) -> Real {
        Real::Integer(x)
    }

    fn d(x: f64) -> Real {
        Real::Double(x)
    }

    fn u(x: &str) -> Uom {
        x.parse().unwrap()
    }

    #[test]
    fn test_default() {
        assert_eq!(
            format!(
                "{}",
                Metric::<Real>::builder().label("name").value(i(42)).build()
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
                    .label("name")
                    .value(i(42))
                    .uom(u("ms"))
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
                    .label("name")
                    .value(i(42))
                    .levels(Levels::try_new(LevelsStrategy::Upper, i(24), i(42)).ok())
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
                    .label("name")
                    .value(i(42))
                    .uom(u("ms"))
                    .levels(Levels::try_new(LevelsStrategy::Upper, i(24), i(42)).ok())
                    .bounds(Some(Bounds {
                        min: i(0),
                        max: i(100)
                    }))
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
                    .label("name")
                    .value(d(42.0))
                    .uom(u("ms"))
                    .levels(Levels::try_new(LevelsStrategy::Upper, d(24.0), d(42.0)).ok())
                    .bounds(Some(Bounds {
                        min: d(0.0),
                        max: d(100.0)
                    }))
                    .build()
            ),
            "name=42.000000ms;24.000000;42.000000;0.000000;100.000000"
        );
    }
}

#[cfg(test)]
mod test_checker_format {
    use super::{CheckResult, Collection, Metric, Real, SimpleCheckResult, State};

    #[test]
    fn test_with_empty_str() {
        assert_eq!(
            SimpleCheckResult::ok_with_details("", ""),
            SimpleCheckResult::ok("")
        );
        assert_eq!(
            SimpleCheckResult::ok_with_details("", ""),
            SimpleCheckResult::notice("")
        );
        assert_eq!(
            SimpleCheckResult::ok_with_details("", ""),
            SimpleCheckResult::new(State::Ok, None, None)
        );
    }

    #[test]
    fn test_single_check_result_ok() {
        let coll = Collection::from(SimpleCheckResult::ok("summary"));
        assert_eq!(coll.state, State::Ok);
        assert_eq!(format!("{}", coll), "summary\nsummary");
    }

    #[test]
    fn test_single_check_result_warn() {
        let coll = Collection::from(SimpleCheckResult::warn("summary"));
        assert_eq!(coll.state, State::Warn);
        assert_eq!(format!("{}", coll), "summary (!)\nsummary (!)");
    }

    #[test]
    fn test_single_check_result_crit() {
        let coll = Collection::from(SimpleCheckResult::crit("summary"));
        assert_eq!(coll.state, State::Crit);
        assert_eq!(format!("{}", coll), "summary (!!)\nsummary (!!)");
    }

    #[test]
    fn test_single_check_result_unknown() {
        let coll = Collection::from(SimpleCheckResult::unknown("summary"));
        assert_eq!(coll.state, State::Unknown);
        assert_eq!(format!("{}", coll), "summary (?)\nsummary (?)");
    }

    #[test]
    fn test_no_check_results_is_ok() {
        let coll = Collection::from(&mut vec![]);
        assert_eq!(coll.state, State::Ok);
        assert_eq!(format!("{}", coll), "OK");
    }

    #[test]
    fn test_merge_check_results_with_state_only() {
        let cr1 = SimpleCheckResult::default();
        let cr2 = SimpleCheckResult::default();
        let cr3 = SimpleCheckResult::default();
        let coll = Collection::from(&mut vec![cr1.into(), cr2.into(), cr3.into()]);
        assert_eq!(coll.state, State::Ok);
        assert_eq!(format!("{}", coll), "OK");
    }

    #[test]
    fn test_merge_check_results_ok() {
        let cr1 = SimpleCheckResult::ok("summary 1");
        let cr2 = SimpleCheckResult::ok("summary 2");
        let cr3 = SimpleCheckResult::ok("summary 3");
        let coll = Collection::from(&mut vec![cr1.into(), cr2.into(), cr3.into()]);
        assert_eq!(coll.state, State::Ok);
        assert_eq!(
            format!("{}", coll),
            "summary 1, summary 2, summary 3\n\
            summary 1\n\
            summary 2\n\
            summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_warn() {
        let cr1 = SimpleCheckResult::ok("summary 1");
        let cr2 = SimpleCheckResult::warn("summary 2");
        let cr3 = SimpleCheckResult::ok("summary 3");
        let coll = Collection::from(&mut vec![cr1.into(), cr2.into(), cr3.into()]);
        assert_eq!(coll.state, State::Warn);
        assert_eq!(
            format!("{}", coll),
            "summary 1, summary 2 (!), summary 3\n\
            summary 1\n\
            summary 2 (!)\n\
            summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_crit() {
        let cr1 = SimpleCheckResult::ok("summary 1");
        let cr2 = SimpleCheckResult::warn("summary 2");
        let cr3 = SimpleCheckResult::crit("summary 3");
        let coll = Collection::from(&mut vec![cr1.into(), cr2.into(), cr3.into()]);
        assert_eq!(coll.state, State::Crit);
        assert_eq!(
            format!("{}", coll),
            "summary 1, summary 2 (!), summary 3 (!!)\n\
            summary 1\n\
            summary 2 (!)\n\
            summary 3 (!!)"
        );
    }

    #[test]
    fn test_merge_check_results_unknown() {
        let cr1 = SimpleCheckResult::ok("summary 1");
        let cr2 = SimpleCheckResult::warn("summary 2");
        let cr3 = SimpleCheckResult::crit("summary 3");
        let cr4 = SimpleCheckResult::unknown("summary 4");
        let coll = Collection::from(&mut vec![cr1.into(), cr2.into(), cr3.into(), cr4.into()]);
        assert_eq!(coll.state, State::Crit);
        assert_eq!(
            format!("{}", coll),
            "summary 1, summary 2 (!), summary 3 (!!), summary 4 (?)\n\
            summary 1\n\
            summary 2 (!)\n\
            summary 3 (!!)\n\
            summary 4 (?)"
        );
    }

    fn m(name: &str, x: isize) -> Metric<Real> {
        Metric::<Real>::builder()
            .label(name)
            .value(Real::Integer(x))
            .build()
    }

    #[test]
    fn test_collection_with_metrics() {
        let cr1 = CheckResult::ok("summary 1", m("m1", 13));
        let cr2 = CheckResult::warn("summary 2", m("m2", 37));
        let cr3 = CheckResult::crit("summary 3", m("m3", 42));
        let mut vec = vec![cr1, cr2, cr3];
        let coll = Collection::from(&mut vec);
        assert_eq!(coll.state, State::Crit);
        assert_eq!(
            format!("{}", coll),
            "summary 1, summary 2 (!), summary 3 (!!) | m1=13;;;; m2=37;;;; m3=42;;;;\n\
            summary 1\n\
            summary 2 (!)\n\
            summary 3 (!!)"
        );
        assert!(vec.is_empty());
    }

    #[test]
    fn test_joined_collection_with_metrics() {
        let mut coll = Collection::default();
        coll.join(&mut Collection::from(&mut vec![CheckResult::ok(
            "summary 1",
            m("m1", 13),
        )]));
        coll.join(&mut Collection::from(&mut vec![CheckResult::warn(
            "summary 2",
            m("m2", 37),
        )]));
        coll.join(&mut Collection::from(&mut vec![CheckResult::crit(
            "summary 3",
            m("m3", 42),
        )]));
        let coll = coll;
        assert_eq!(coll.state, State::Crit);
        assert_eq!(
            format!("{}", coll),
            "summary 1, summary 2 (!), summary 3 (!!) | m1=13;;;; m2=37;;;; m3=42;;;;\n\
            summary 1\n\
            summary 2 (!)\n\
            summary 3 (!!)"
        );
    }

    #[test]
    fn test_collection_with_details() {
        let cr_ok = SimpleCheckResult::ok_with_details("summary ok", "details ok");
        let cr_notice = SimpleCheckResult::notice("notice");
        let cr_warn = SimpleCheckResult::warn_with_details("summary warn", "details warn");
        let cr_crit = SimpleCheckResult::crit_with_details("summary crit", "details crit");
        let coll = Collection::from(&mut vec![
            cr_ok.into(),
            cr_notice.into(),
            cr_warn.into(),
            cr_crit.into(),
        ]);
        assert_eq!(coll.state, State::Crit);
        assert_eq!(
            format!("{}", coll),
            "summary ok, summary warn (!), summary crit (!!)\n\
            details ok\n\
            notice\n\
            details warn (!)\n\
            details crit (!!)"
        );
    }

    #[test]
    fn test_collection_with_metrics_and_details() {
        let cr_ok = SimpleCheckResult::ok("summary ok");
        let cr_notice = SimpleCheckResult::notice("notice");
        let cr_warn =
            CheckResult::warn_with_details("summary warn", "details warn", m("mwarn", 13));
        let cr_crit =
            CheckResult::crit_with_details("summary crit", "details crit", m("mcrit", 37));
        let coll = Collection::from(&mut vec![cr_ok.into(), cr_notice.into(), cr_warn, cr_crit]);
        assert_eq!(coll.state, State::Crit);
        assert_eq!(
            format!("{}", coll),
            "summary ok, summary warn (!), summary crit (!!) | mwarn=13;;;; mcrit=37;;;;\n\
            summary ok\n\
            notice\n\
            details warn (!)\n\
            details crit (!!)"
        );
    }

    #[test]
    fn test_collection_with_heterogeneous_details() {
        let cr_ok = SimpleCheckResult::ok("summary ok");
        let cr_notice = SimpleCheckResult::notice("notice");
        let cr_warn =
            CheckResult::warn_with_details("summary warn", "details warn", m("mwarn", 13));
        let cr_crit = CheckResult::crit("summary crit", m("mcrit", 37));
        let coll = Collection::from(&mut vec![cr_ok.into(), cr_notice.into(), cr_warn, cr_crit]);
        assert_eq!(coll.state, State::Crit);
        assert_eq!(
            format!("{}", coll),
            "summary ok, summary warn (!), summary crit (!!) | mwarn=13;;;; mcrit=37;;;;\n\
            summary ok\n\
            notice\n\
            details warn (!)\n\
            summary crit (!!)"
        );
    }
}

#[cfg(test)]
mod test_from_levels_format {
    use super::{CheckResult, Collection, Levels, LevelsStrategy, Metric, Real, State, Uom};

    #[test]
    fn test_check_ok() {
        let metric = Metric::builder()
            .label("label")
            .value(5)
            .uom(Uom("ms".to_string()))
            .levels(Levels::try_new(LevelsStrategy::Upper, 10, 20).ok())
            .build();
        let check = CheckResult::from_levels("summary", metric);
        let coll = Collection::from(&mut vec![check.map(Real::from)]);
        assert_eq!(coll.state, State::Ok);
        assert_eq!(
            format!("{}", coll),
            "summary (warn/crit at 10/20) | label=5ms;10;20;;\nsummary (warn/crit at 10/20)"
        );
    }

    #[test]
    fn test_notice_ok() {
        let metric = Metric::builder()
            .label("label")
            .value(5)
            .uom(Uom("ms".to_string()))
            .levels(Levels::try_new(LevelsStrategy::Upper, 10, 20).ok())
            .build();
        let check = CheckResult::notice_from_levels("notice", metric);
        let coll = Collection::from(&mut vec![check.map(Real::from)]);
        assert_eq!(coll.state, State::Ok);
        assert_eq!(
            format!("{}", coll),
            "OK | label=5ms;10;20;;\nnotice (warn/crit at 10/20)"
        );
    }

    #[test]
    fn test_notice_warn() {
        let metric = Metric::builder()
            .label("label")
            .value(15)
            .uom(Uom("ms".to_string()))
            .levels(Levels::try_new(LevelsStrategy::Upper, 10, 20).ok())
            .build();
        let check = CheckResult::notice_from_levels("notice", metric);
        let coll = Collection::from(&mut vec![check.map(Real::from)]);
        assert_eq!(coll.state, State::Warn);
        assert_eq!(
            format!("{}", coll),
            "notice (warn/crit at 10/20) (!) | label=15ms;10;20;;\nnotice (warn/crit at 10/20) (!)"
        );
    }

    #[test]
    fn test_notice_crit() {
        let metric = Metric::builder()
            .label("label")
            .value(50)
            .uom(Uom("ms".to_string()))
            .levels(Levels::try_new(LevelsStrategy::Upper, 10, 20).ok())
            .build();
        let check = CheckResult::notice_from_levels("notice", metric);
        let coll = Collection::from(&mut vec![check.map(Real::from)]);
        assert_eq!(coll.state, State::Crit);
        assert_eq!(
            format!("{}", coll),
            "notice (warn/crit at 10/20) (!!) | label=50ms;10;20;;\nnotice (warn/crit at 10/20) (!!)"
        );
    }
}
