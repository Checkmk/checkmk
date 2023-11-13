// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::checking::{CheckResult, State};
use std::fmt::{Display, Formatter, Result as FormatResult};

pub struct Output {
    pub worst_state: State,
    check_results: Vec<CheckResult>,
}

impl Display for Output {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        fn write_joined<T: Display>(
            f: &mut Formatter,
            mut iter: impl Iterator<Item = T>,
            start: &'static str,
            joiner: &'static str,
        ) -> FormatResult {
            if let Some(item) = iter.next() {
                write!(f, "{}{}", start, item)?;
            };
            // This does essentially what
            // iter.map(ToString::to_string).collect::<Vec<_>>().join(joiner) does,
            // but without the need to allocate some Strings and a Vec.
            for item in iter {
                write!(f, "{}{}", joiner, item)?;
            }
            Ok(())
        }

        write!(f, "HTTP {}", self.worst_state)?;

        let summaries = self
            .check_results
            .iter()
            .filter_map(|cr| match cr {
                CheckResult::Summary(check_item) => Some(check_item),
                _ => None,
            })
            .filter(|summ| !summ.text.is_empty());
        write_joined(f, summaries, " - ", ", ")?;

        let metrics = self.check_results.iter().filter_map(|cr| match cr {
            CheckResult::Metric(metric_item) => Some(metric_item),
            _ => None,
        });
        write_joined(f, metrics, " | ", " ")?;

        Ok(())
    }
}

impl Output {
    pub fn from_check_results(check_results: Vec<CheckResult>) -> Self {
        let worst_state = match check_results
            .iter()
            .filter_map(|cr| match cr {
                CheckResult::Summary(check_item) => Some(&check_item.state),
                _ => None,
            })
            .max()
        {
            Some(state) => state.clone(),
            None => State::Ok,
        };

        Self {
            worst_state,
            check_results,
        }
    }
}

#[cfg(test)]
mod test_output_format {
    use super::*;
    use crate::checking::{CheckItem, Metric};

    fn summary(state: State, text: &str) -> CheckResult {
        CheckResult::Summary(CheckItem {
            state,
            text: text.to_string(),
        })
    }

    fn metric(
        name: &str,
        value: f64,
        unit: Option<&'static str>,
        levels: Option<(f64, Option<f64>)>,
        lower: Option<f64>,
        upper: Option<f64>,
    ) -> CheckResult {
        CheckResult::Metric(Metric {
            name: name.to_string(),
            value,
            unit,
            levels,
            lower,
            upper,
        })
    }

    #[test]
    fn test_no_check_results_is_ok() {
        assert_eq!(format!("{}", Output::from_check_results(vec![])), "HTTP OK");
    }

    #[test]
    fn test_merge_check_results_with_state_only() {
        let cr1 = summary(State::Ok, "");
        let cr2 = summary(State::Ok, "");
        let cr3 = summary(State::Ok, "");
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3])),
            "HTTP OK"
        );
    }

    #[test]
    fn test_merge_check_results_ok() {
        let cr1 = summary(State::Ok, "summary 1");
        let cr2 = summary(State::Ok, "summary 2");
        let cr3 = summary(State::Ok, "summary 3");
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3])),
            "HTTP OK - summary 1, summary 2, summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_warn() {
        let cr1 = summary(State::Ok, "summary 1");
        let cr2 = summary(State::Warn, "summary 2");
        let cr3 = summary(State::Ok, "summary 3");
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3])),
            "HTTP WARNING - summary 1, summary 2 (!), summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_crit() {
        let cr1 = summary(State::Ok, "summary 1");
        let cr2 = summary(State::Warn, "summary 2");
        let cr3 = summary(State::Crit, "summary 3");
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3])),
            "HTTP CRITICAL - summary 1, summary 2 (!), summary 3 (!!)"
        );
    }

    #[test]
    fn test_merge_check_results_unknown() {
        let cr1 = summary(State::Ok, "summary 1");
        let cr2 = summary(State::Warn, "summary 2");
        let cr3 = summary(State::Crit, "summary 3");
        let cr4 = summary(State::Unknown, "summary 4");
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3, cr4])),
            "HTTP UNKNOWN - summary 1, summary 2 (!), summary 3 (!!), summary 4 (?)"
        );
    }

    #[test]
    fn test_merge_empty_summary_basic_metric() {
        let cr1 = summary(State::Ok, "");
        let m1 = metric("my_metric", 123., None, None, None, None);
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, m1])),
            "HTTP OK | my_metric=123;;;;"
        );
    }

    #[test]
    fn test_merge_one_summary_one_metric() {
        let cr1 = summary(State::Warn, "summary 1");
        let m1 = metric(
            "my_metric",
            123.,
            Some("s"),
            Some((1., Some(2.))),
            Some(0.),
            Some(100.),
        );
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, m1])),
            "HTTP WARNING - summary 1 (!) | my_metric=123s;1;2;0;100"
        );
    }

    #[test]
    fn test_merge_float_metric() {
        let m1 = metric(
            "my_metric",
            123.1,
            Some("s"),
            Some((1.2, Some(2.3))),
            Some(0.1),
            Some(100.2),
        );
        assert_eq!(
            format!("{}", Output::from_check_results(vec![m1])),
            "HTTP OK | my_metric=123.1s;1.2;2.3;0.1;100.2"
        );
    }

    #[test]
    fn test_merge_two_metrics() {
        let m1 = metric("my_metric_1", 1., None, None, None, None);
        let m2 = metric("my_metric_2", 2., None, None, None, None);
        assert_eq!(
            format!("{}", Output::from_check_results(vec![m1, m2])),
            "HTTP OK | my_metric_1=1;;;; my_metric_2=2;;;;"
        );
    }
}
