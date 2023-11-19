// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::fmt::{Display, Formatter, Result as FormatResult};

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
