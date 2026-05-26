// Copyright (C) 2026 Checkmk GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

pub enum Label<'a> {
    Block(&'a str),
    Inline,
}

pub trait PerfLog {
    fn is_debug_enabled(&self) -> bool;
    fn debug(&mut self, msg: &str);
}

pub struct RealLog;

// Enforces use of PerfTimer by callers.
// Useful to warn if callers did not call stop.
#[must_use]
pub struct PerfTimer<Logger: PerfLog = RealLog> {
    tag: &'static str,
    label: Option<String>,
    start: Option<std::time::Instant>,
    logger: Logger,
}

impl<Logger: PerfLog> PerfTimer<Logger> {
    // Label::Block logs open/close lines around a labelled span, eg:
    //   [section] <<<oracle_performance:sep(124)>>>
    //     ... child measurements ...
    //   [/section] <<<oracle_performance:sep(124)>>> took 0.537s
    //
    // Label::Inline logs a single line on stop, eg:
    //   [query] took 0.149s
    pub fn start_with(tag: &'static str, label: Label<'_>, mut logger: Logger) -> Self {
        if !logger.is_debug_enabled() {
            return PerfTimer {
                tag: "",
                label: None,
                start: None,
                logger,
            };
        }

        let label = match label {
            Label::Block(l) => {
                logger.debug(&format!("[{}] {}", tag, l));
                Some(l.to_owned())
            }
            Label::Inline => None,
        };
        PerfTimer {
            tag,
            label,
            start: Some(std::time::Instant::now()),
            logger,
        }
    }

    pub fn stop(mut self) {
        if !self.logger.is_debug_enabled() {
            return;
        }

        let Some(start) = self.start else { return };
        let elapsed = start.elapsed().as_secs_f64();
        self.logger.debug(&match &self.label {
            Some(label) => format!("[/{}] {} took {:.3}s", self.tag, label, elapsed),
            None => format!("[{}] took {:.3}s", self.tag, elapsed),
        });
    }
}

impl PerfTimer<RealLog> {
    // Convenience constructor using the real logger.
    pub fn start(tag: &'static str, label: Label<'_>) -> Self {
        Self::start_with(tag, label, RealLog)
    }
}

impl PerfLog for RealLog {
    fn is_debug_enabled(&self) -> bool {
        log::log_enabled!(log::Level::Debug)
    }
    fn debug(&mut self, msg: &str) {
        log::debug!("{}", msg);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockLog {
        debug_enabled: bool,
        messages: Vec<String>,
    }

    impl PerfLog for &mut MockLog {
        fn is_debug_enabled(&self) -> bool {
            self.debug_enabled
        }
        fn debug(&mut self, msg: &str) {
            self.messages.push(msg.to_owned());
        }
    }

    #[test]
    fn inline_logs_single_line_on_stop() {
        let mut log = MockLog {
            debug_enabled: true,
            messages: vec![],
        };

        PerfTimer::start_with("query", Label::Inline, &mut log).stop();

        assert_eq!(log.messages.len(), 1);
        assert!(log.messages[0].starts_with("[query] took "));
        assert!(log.messages[0].ends_with('s'));
    }

    #[test]
    fn block_logs_open_line_on_start_and_close_line_on_stop() {
        let mut log = MockLog {
            debug_enabled: true,
            messages: vec![],
        };

        PerfTimer::start_with("section", Label::Block("my_label"), &mut log).stop();

        assert_eq!(log.messages.len(), 2);
        assert_eq!(log.messages[0], "[section] my_label");
        assert!(log.messages[1].starts_with("[/section] my_label took "));
        assert!(log.messages[1].ends_with('s'));
    }

    #[test]
    fn inline_elapsed_reflects_real_time() {
        let mut log = MockLog {
            debug_enabled: true,
            messages: vec![],
        };

        let timer = PerfTimer::start_with("query", Label::Inline, &mut log);
        std::thread::sleep(std::time::Duration::from_millis(10));
        timer.stop();

        let elapsed = parse_elapsed(&log.messages[0]);
        assert!(
            elapsed >= 0.009,
            "expected >= 9ms, got {:.1}ms",
            elapsed * 1000.0
        );
    }

    #[test]
    fn block_elapsed_reflects_real_time() {
        let mut log = MockLog {
            debug_enabled: true,
            messages: vec![],
        };

        let timer = PerfTimer::start_with("section", Label::Block("lbl"), &mut log);
        std::thread::sleep(std::time::Duration::from_millis(10));
        timer.stop();

        let elapsed = parse_elapsed(&log.messages[1]);
        assert!(
            elapsed >= 0.009,
            "expected >= 9ms, got {:.1}ms",
            elapsed * 1000.0
        );
    }

    #[test]
    fn inactive_timer_logs_nothing() {
        let mut log = MockLog {
            debug_enabled: false,
            messages: vec![],
        };

        let timer = PerfTimer::start_with("tag", Label::Block("label"), &mut log);
        timer.stop();

        assert!(log.messages.is_empty());
    }

    // Parses the seconds value from the end of a log line, eg "... took 0.012s" -> 0.012
    fn parse_elapsed(msg: &str) -> f64 {
        msg.trim_end_matches('s')
            .rsplit_once(' ')
            .expect("expected 'took <elapsed>s'")
            .1
            .parse()
            .expect("elapsed should be a number")
    }
}
