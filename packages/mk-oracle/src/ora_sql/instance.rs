// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self, OracleConfig};
use crate::ora_sql::backend::{make_spot, Spot};
use crate::ora_sql::custom::get_sql_dir;
use crate::ora_sql::section::Section;
use crate::ora_sql::system::WorkInstances;
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
    // TODO: detect instances
    // TODO: apply to config detected instances
    // TODO: customize instances
    // TODO: resulting in the list of endpoints
    let all = calc_spots(vec![ora_sql.endpoint()]);
    let connected = connect_spots(all);

    let mut _output = String::new();
    let _r = connected
        .into_iter()
        .map(|spot| {
            let instances = WorkInstances::new(&spot);

            let sections = ora_sql
                .product()
                .sections()
                .iter()
                .map(|s| Section::new(s, ora_sql.product().cache_age()))
                .collect::<Vec<_>>();
            // TODO: remove it after code is working
            #[allow(clippy::for_kv_map)]
            for (_instance, _version) in instances.all() {
                for section in &sections {
                    let section_name = section.name();
                    log::info!("Generating data for instance: {}", section_name);
                    section.select_query(get_sql_dir(), 0).map_or_else(
                        || {
                            log::warn!("No query found for section: {}", section_name);
                            "No query found".to_string()
                        },
                        |query| {
                            log::info!("Found query for section {}: {}", section_name, query);
                            // Here you would execute the query and process the results
                            // For now, we just return the query as a placeholder
                            format!("Query for {}: {}", section_name, query)
                        },
                    );
                }
            }
            // Add more data generation here as needed
            "section_name".to_owned()
        })
        .collect::<Vec<String>>()
        .join("\n");

    Ok("nothing".to_string())
}

// tested only in integration tests
fn connect_spots(spots: Vec<Spot>) -> Vec<Spot> {
    let connected = spots
        .into_iter()
        .filter_map(|mut t| {
            if let Err(e) = t.connect() {
                log::error!("Error connecting to instance: {}", e);
                None
            } else {
                log::info!("Connected to instance: {:?}", t.target());
                Some(t)
            }
        })
        .collect::<Vec<Spot>>();
    log::info!(
        "CONNECTED SPOTS: {:?}",
        connected.iter().map(|t| t.target()).collect::<Vec<_>>()
    );

    connected
}

fn calc_spots(endpoints: Vec<config::ora_sql::Endpoint>) -> Vec<Spot> {
    log::info!("ENDPOINTS: {:?}", endpoints);
    endpoints
        .into_iter()
        .filter_map(|ep| {
            make_spot(&ep).map_or_else(
                |error| {
                    log::error!("Error creating spot for endpoint {error}");
                    None
                },
                Some,
            )
        })
        .collect::<Vec<Spot>>()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calc_spots() {
        assert!(calc_spots(vec![]).is_empty());
        let all = calc_spots(vec![
            config::ora_sql::Endpoint::default(),
            config::ora_sql::Endpoint::default(),
        ]);
        assert_eq!(all.len(), 2);
    }
}
