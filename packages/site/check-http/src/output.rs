// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::checking_types::{CheckResult, State};
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

        let summaries = self.check_results.iter().filter_map(|cr| match cr {
            CheckResult::Summary(check_item) => Some(check_item),
            _ => None,
        });
        write_joined(f, summaries, "", ", ")?;

        let metrics = self.check_results.iter().filter_map(|cr| match cr {
            CheckResult::Metric(metric_item) => Some(metric_item),
            _ => None,
        });
        write_joined(f, metrics, " | ", " ")?;

        let details = self.check_results.iter().filter_map(|cr| match cr {
            CheckResult::Details(check_item) => Some(check_item),
            _ => None,
        });
        write_joined(f, details, "\n", "\n")?;

        Ok(())
    }
}

impl Output {
    pub fn from_check_results(check_results: Vec<CheckResult>) -> Self {
        let worst_state = match check_results
            .iter()
            .filter_map(|cr| match cr {
                CheckResult::Summary(check_item) | CheckResult::Details(check_item) => {
                    Some(&check_item.state)
                }
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
    use crate::checking_types::UpperLevels;

    fn summary(state: State, text: &str) -> CheckResult {
        CheckResult::summary(state, text).unwrap()
    }

    fn details(state: State, text: &str) -> CheckResult {
        CheckResult::details(state, text).unwrap()
    }

    fn metric(
        name: &str,
        value: f64,
        unit: Option<char>,
        levels: Option<UpperLevels<f64>>,
        lower: Option<f64>,
        upper: Option<f64>,
    ) -> CheckResult {
        CheckResult::metric(name, value, unit, levels, lower, upper).unwrap()
    }

    #[test]
    fn test_no_check_results_is_ok() {
        assert_eq!(format!("{}", Output::from_check_results(vec![])), "");
    }

    #[test]
    #[should_panic]
    fn test_merge_check_results_with_state_only() {
        let _ = summary(State::Ok, "");
    }

    #[test]
    fn test_merge_check_results_ok() {
        let cr1 = summary(State::Ok, "summary 1");
        let cr2 = summary(State::Ok, "summary 2");
        let cr3 = details(State::Ok, "details 3");
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3])),
            "summary 1, summary 2\ndetails 3"
        );
    }

    #[test]
    fn test_merge_check_results_warn() {
        let cr1 = summary(State::Ok, "summary 1");
        let cr2 = summary(State::Warn, "summary 2");
        let cr3 = summary(State::Ok, "summary 3");
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3])),
            "summary 1, summary 2 (!), summary 3"
        );
    }

    #[test]
    fn test_merge_check_results_crit() {
        let cr1 = summary(State::Ok, "summary 1");
        let cr2 = summary(State::Warn, "summary 2");
        let cr3 = details(State::Crit, "details 3");
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3])),
            "summary 1, summary 2 (!)\ndetails 3 (!!)"
        );
    }

    #[test]
    fn test_merge_check_results_unknown() {
        let cr1 = summary(State::Ok, "summary 1");
        let cr2 = details(State::Warn, "details 2");
        let cr3 = details(State::Crit, "details 3");
        let cr4 = summary(State::Unknown, "summary 4");
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, cr2, cr3, cr4])),
            "summary 1, summary 4 (?)\ndetails 2 (!)\ndetails 3 (!!)"
        );
    }

    #[test]
    fn test_basic_metric() {
        let m1 = metric("my_metric", 123., None, None, None, None);
        assert_eq!(
            format!("{}", Output::from_check_results(vec![m1])),
            " | my_metric=123;;;;"
        );
    }

    #[test]
    fn test_merge_one_summary_one_metric() {
        let cr1 = summary(State::Warn, "summary 1");
        let m1 = metric(
            "my_metric",
            123.,
            Some('s'),
            Some(UpperLevels::warn_crit(1., 2.)),
            Some(0.),
            Some(100.),
        );
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, m1])),
            "summary 1 (!) | my_metric=123s;1;2;0;100"
        );
    }

    #[test]
    fn test_merge_float_metric() {
        let m1 = metric(
            "my_metric",
            123.1,
            Some('s'),
            Some(UpperLevels::warn_crit(1.2, 2.3)),
            Some(0.1),
            Some(100.2),
        );
        assert_eq!(
            format!("{}", Output::from_check_results(vec![m1])),
            " | my_metric=123.1s;1.2;2.3;0.1;100.2"
        );
    }

    #[test]
    fn test_merge_two_metrics() {
        let m1 = metric("my_metric_1", 1., None, None, None, None);
        let m2 = metric("my_metric_2", 2., None, None, None, None);
        assert_eq!(
            format!("{}", Output::from_check_results(vec![m1, m2])),
            " | my_metric_1=1;;;; my_metric_2=2;;;;"
        );
    }

    #[test]
    fn test_merge_summary_details_metrics() {
        let cr1 = summary(State::Ok, "summary 1");
        let cr2 = details(State::Warn, "details 2");
        let cr3 = details(State::Crit, "details 3");
        let cr4 = summary(State::Ok, "summary 4");
        let m1 = metric("my_metric_1", 1., None, None, None, None);
        let m2 = metric("my_metric_2", 2., None, None, None, None);
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, m1, cr2, m2, cr3, cr4])),
            "summary 1, summary 4 | my_metric_1=1;;;; my_metric_2=2;;;;\ndetails 2 (!)\ndetails 3 (!!)"
        );
    }

    #[test]
    fn test_cleanup_pipe() {
        let cr1 = summary(State::Ok, "pattern1|pattern2");
        let cr2 = details(State::Warn, "details 1");
        let m1 = metric("my_metric_1", 1., None, None, None, None);
        assert_eq!(
            format!("{}", Output::from_check_results(vec![cr1, m1, cr2])),
            // first "pipe" symbol is actually a light vertical bar
            "pattern1❘pattern2 | my_metric_1=1;;;;\ndetails 1 (!)"
        );
    }
}
