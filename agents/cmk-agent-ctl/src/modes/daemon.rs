// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config;
use crate::modes::{pull, push};
use anyhow::Result as AnyhowResult;
use std::sync::mpsc;
use std::thread;

pub fn daemon(
    registry: config::Registry,
    pull_config: config::PullConfig,
    client_config: config::ClientConfig,
) -> AnyhowResult<()> {
    let (tx_push, rx) = mpsc::channel();
    let tx_pull = tx_push.clone();
    thread::spawn(move || {
        tx_push.send(push::push(registry, client_config)).unwrap();
    });
    thread::spawn(move || {
        tx_pull.send(pull::pull(pull_config)).unwrap();
    });

    // We should never receive anything here, unless one of the threads crashed.
    // In that case, this will contain an error that should be propagated.
    rx.recv().unwrap()
}
