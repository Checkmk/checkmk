// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self, OracleConfig};
use crate::setup::Env;
use crate::utils;

use anyhow::Result;

impl OracleConfig {
    pub async fn exec(&self, environment: &Env) -> Result<String> {
        if let Some(ora_sql) = self.ora_sql() {
            OracleConfig::prepare_cache_sub_dir(environment, &ora_sql.config_cache_dir());
            log::info!("Generating main data");
            let mut output: Vec<String> = Vec::new();
            output.push(
                generate_data(ora_sql, environment)
                    .await
                    .unwrap_or_else(|e| {
                        log::error!("Error generating data at main config: {e}");
                        format!("{e}\n")
                    }),
            );
            for (num, config) in std::iter::zip(0.., ora_sql.configs()) {
                log::info!("Generating configs data");
                OracleConfig::prepare_cache_sub_dir(environment, &config.config_cache_dir());
                let configs_data = generate_data(config, environment)
                    .await
                    .unwrap_or_else(|e| {
                        log::error!("Error generating data at config {num}: {e}");
                        format!("{e}\n")
                    });
                output.push(configs_data);
            }
            Ok(output.join(""))
        } else {
            log::error!("No config");
            anyhow::bail!("No Config")
        }
    }

    fn prepare_cache_sub_dir(environment: &Env, hash: &str) {
        match environment.obtain_cache_sub_dir(hash).map(utils::touch_dir) {
            Some(Err(e)) => log::error!("Error touching dir: {e}, caching may be not possible"),
            Some(Ok(p)) => log::info!("Using cache dir {p:?}"),
            None => log::warn!("No cache dir defined, caching is not possible"),
        }
    }
}

/// Generate data as defined by config
/// Consists from two parts: instance entries + sections for every instance
async fn generate_data(ora_sql: &config::ora_sql::Config, _environment: &Env) -> Result<String> {
    use crate::ora_sql::backend::make_task;
    let _task = make_task(&ora_sql.endpoint());
    Ok("nothing".to_string())
}
