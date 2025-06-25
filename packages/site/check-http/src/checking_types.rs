// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::fmt::{Display, Formatter, Result as FormatResult};

// check_http allows specification of
// * no levels/bounds
// * warn/lower
// * warn/lower and crit/upper
// So we're modelling exactly this.

#[cfg_attr(test, derive(PartialEq, Debug))]
pub struct UpperLevels<T> {
    pub warn: T,
    pub crit: Option<T>,
}

impl<T> UpperLevels<T>
where
    T: PartialOrd,
{
    pub fn warn(warn: T) -> Self {
        Self { warn, crit: None }
    }

    pub fn warn_crit(warn: T, crit: T) -> Self {
        Self {
            warn,
            crit: Some(crit),
        }
    }

    pub fn evaluate(&self, value: &T) -> Option<State> {
        match self {
            Self {
                warn: _,
                crit: Some(crit),
            } if value >= crit => Some(State::Crit),
            Self { warn, crit: _ } if value >= warn => Some(State::Warn),
            _ => None,
        }
    }
}

impl From<UpperLevels<u64>> for UpperLevels<f64> {
    fn from(value: UpperLevels<u64>) -> Self {
        Self {
            warn: value.warn as f64,
            crit: value.crit.map(|c| c as f64),
        }
    }
}

#[cfg_attr(test, derive(PartialEq))]
pub struct LowerLevels<T> {
    pub warn: T,
    pub crit: Option<T>,
}

impl<T> LowerLevels<T>
where
    T: PartialOrd,
{
    pub fn warn(warn: T) -> Self {
        Self { warn, crit: None }
    }

    pub fn warn_crit(warn: T, crit: T) -> Self {
        Self {
            warn,
            crit: Some(crit),
        }
    }

    pub fn evaluate(&self, value: &T) -> Option<State> {
        match self {
            Self {
                warn: _,
                crit: Some(crit),
            } if value < crit => Some(State::Crit),
            Self { warn, crit: _ } if value < warn => Some(State::Warn),
            _ => None,
        }
    }
}
pub struct Bounds<T> {
    pub lower: T,
    pub upper: Option<T>,
}

impl<T> Bounds<T>
where
    T: PartialOrd,
{
    pub fn lower(lower: T) -> Self {
        Self { lower, upper: None }
    }

    pub fn lower_upper(lower: T, upper: T) -> Self {
        Self {
            lower,
            upper: Some(upper),
        }
    }

    pub fn evaluate(&self, value: &T, severity: State) -> Option<State> {
        match self {
            Self {
                lower: _,
                upper: Some(upper),
            } if value > upper => Some(severity),
            Self { lower, upper: _ } if value < lower => Some(severity),
            _ => None,
        }
    }
}
#[cfg_attr(test, derive(Debug))]
#[derive(Clone, PartialEq, Eq, PartialOrd, Ord)]
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

impl From<State> for i32 {
    fn from(value: State) -> Self {
        match value {
            State::Ok => 0,
            State::Warn => 1,
            State::Crit => 2,
            State::Unknown => 3,
        }
    }
}

#[cfg_attr(test, derive(PartialEq, Debug))]
pub struct Metric {
    pub name: String,
    pub value: f64,
    pub unit: Option<char>,
    pub levels: Option<UpperLevels<f64>>,
    pub lower: Option<f64>,
    pub upper: Option<f64>,
}

impl Display for Metric {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        fn write_optional<T: Display>(f: &mut Formatter, val: Option<T>) -> FormatResult {
            if let Some(val) = val {
                write!(f, "{}", val)?;
            };
            Ok(())
        }

        write!(f, "{}={}", self.name, self.value)?;
        write_optional(f, self.unit)?;
        let (warn, crit) = match self.levels {
            Some(UpperLevels { warn, crit }) => (Some(warn), crit),
            None => (None, None),
        };
        write!(f, ";")?;
        write_optional(f, warn)?;
        write!(f, ";")?;
        write_optional(f, crit)?;
        write!(f, ";")?;
        write_optional(f, self.lower)?;
        write!(f, ";")?;
        write_optional(f, self.upper)?;
        Ok(())
    }
}

#[cfg_attr(test, derive(Eq, PartialEq, Debug))]
pub struct CheckItem {
    pub state: State,
    text: String,
}

impl Display for CheckItem {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "{}{}",
            // The pipe symbol indicates end of service output and start of metrics.
            // Replace any (e.g. due to the expected regex) in the output by a Unicode "Light vertical bar"
            self.text.replace('|', "\u{2758}"),
            match self.state {
                State::Ok => "",
                State::Warn => " (!)",
                State::Crit => " (!!)",
                State::Unknown => " (?)",
            }
        )
    }
}

impl CheckItem {
    fn new(state: State, text: &str) -> Option<Self> {
        if text.is_empty() {
            return None;
        };

        Some(Self {
            state,
            text: text.to_string(),
        })
    }
}

#[cfg_attr(test, derive(PartialEq, Debug))]
pub enum CheckResult {
    Summary(CheckItem),
    Details(CheckItem),
    Metric(Metric),
}

impl CheckResult {
    pub fn summary(state: State, text: &str) -> Option<CheckResult> {
        CheckItem::new(state, text).map(Self::Summary)
    }

    pub fn details(state: State, text: &str) -> Option<CheckResult> {
        CheckItem::new(state, text).map(Self::Details)
    }

    pub fn metric(
        name: &str,
        value: f64,
        unit: Option<char>,
        levels: Option<UpperLevels<f64>>,
        lower: Option<f64>,
        upper: Option<f64>,
    ) -> Option<CheckResult> {
        Some(CheckResult::Metric(Metric {
            name: name.to_string(),
            value,
            unit,
            levels,
            lower,
            upper,
        }))
    }
}

pub fn notice(state: State, text: &str) -> Vec<Option<CheckResult>> {
    let details = CheckResult::details(state.clone(), text);
    match state {
        State::Ok => vec![details],
        _ => vec![CheckResult::summary(state.clone(), text), details],
    }
}

pub fn check_upper_levels<T: Display + Copy + PartialOrd, U: Display, F: Fn(&T) -> U>(
    description: &str,
    value: T,
    render_func: F,
    upper_levels: &Option<UpperLevels<T>>,
) -> Vec<Option<CheckResult>> {
    let state = match &upper_levels {
        Some(ul) => ul.evaluate(&value).unwrap_or(State::Ok),
        None => State::Ok,
    };

    let warn_crit_info = if let State::Warn | State::Crit = state {
        match &upper_levels {
            Some(UpperLevels { warn, crit: None }) => format!(" (warn at {})", render_func(warn)),
            Some(UpperLevels {
                warn,
                crit: Some(crit),
            }) => format!(
                " (warn/crit at {}/{})",
                render_func(warn),
                render_func(crit)
            ),
            _ => "".to_string(),
        }
    } else {
        "".to_string()
    };

    notice(
        state,
        &format!("{}: {}{}", description, render_func(&value), warn_crit_info),
    )
}

// TODO(au): We could avoid some code duplication by handling
// upper/lower levels more genericly with a Trait.
// However, for now, the amount of duplicated code seems acceptable
pub fn check_lower_levels<T: Display + Copy + PartialOrd, U: Display, F: Fn(&T) -> U>(
    description: &str,
    value: T,
    render_func: F,
    lower_levels: &Option<LowerLevels<T>>,
) -> Vec<Option<CheckResult>> {
    let state = match &lower_levels {
        Some(ul) => ul.evaluate(&value).unwrap_or(State::Ok),
        None => State::Ok,
    };

    let warn_crit_info = if let State::Warn | State::Crit = state {
        match &lower_levels {
            Some(LowerLevels { warn, crit: None }) => {
                format!(" (warn below {})", render_func(warn))
            }
            Some(LowerLevels {
                warn,
                crit: Some(crit),
            }) => format!(
                " (warn/crit below {}/{})",
                render_func(warn),
                render_func(crit)
            ),
            _ => "".to_string(),
        }
    } else {
        "".to_string()
    };

    notice(
        state,
        &format!("{}: {}{}", description, render_func(&value), warn_crit_info),
    )
}

#[cfg(test)]
mod test_check_levels {
    use super::*;

    #[test]
    fn test_basic() {
        assert!(
            check_upper_levels("test", 0, u64::to_string, &None)
                == vec![CheckResult::details(State::Ok, "test: 0")]
        )
    }

    #[test]
    fn test_warn_level_inactive() {
        assert!(
            check_upper_levels(
                "test",
                0,
                |b| format!("{} Bytes", b),
                &Some(UpperLevels::warn(10))
            ) == vec![CheckResult::details(State::Ok, "test: 0 Bytes")]
        )
    }

    #[test]
    fn test_warn_level_active() {
        assert!(
            check_upper_levels(
                "test",
                20,
                |p| format!("{}%", p),
                &Some(UpperLevels::warn(10))
            ) == vec![
                CheckResult::summary(State::Warn, "test: 20% (warn at 10%)"),
                CheckResult::details(State::Warn, "test: 20% (warn at 10%)")
            ]
        )
    }

    #[test]
    fn test_warn_crit_levels() {
        assert!(
            check_upper_levels(
                "test",
                20,
                |p| format!("{}%", p),
                &Some(UpperLevels::warn_crit(10, 20))
            ) == vec![
                CheckResult::summary(State::Crit, "test: 20% (warn/crit at 10%/20%)"),
                CheckResult::details(State::Crit, "test: 20% (warn/crit at 10%/20%)")
            ]
        )
    }
}
