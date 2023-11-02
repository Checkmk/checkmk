// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::fmt::{Display, Formatter, Result as FormatResult};

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

impl State {
    fn as_marker(&self) -> &'static str {
        match self {
            State::Ok => "",
            State::Warn => " (!)",
            State::Crit => " (!!)",
            State::Unknown => " (?)",
        }
    }
}

pub struct Output {
    pub state: State,
    pub summary: Option<String>,
    pub details: Option<String>,
}

impl Display for Output {
    fn fmt(&self, f: &mut Formatter) -> FormatResult {
        write!(f, "HTTP {}", self.state)?;
        if let Some(summary) = self.summary.as_ref() {
            write!(f, " - {}", summary)?;
        }
        if let Some(details) = self.details.as_ref() {
            write!(f, "\n{}", details)?;
        }
        Ok(())
    }
}

impl Output {
    pub fn from_summary(state: State, summary: &str) -> Self {
        let summary = format!("{}{}", summary, state.as_marker());
        Self {
            state,
            summary: Some(summary),
            details: None,
        }
    }

    pub fn from_state(state: State) -> Self {
        Self {
            state,
            summary: None,
            details: None,
        }
    }
}
