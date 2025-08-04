// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self, OracleConfig};
use crate::ora_sql::backend::{make_spot, ClosedSpot, OpenedSpot};
use crate::ora_sql::custom::get_sql_dir;
use crate::ora_sql::section::Section;
use crate::ora_sql::system::WorkInstances;
use crate::setup::Env;
use crate::types::{InstanceName, Separator, SqlQuery};
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

type InstanceWorks = (InstanceName, Vec<(SqlQuery, String)>);
type SpotWorks = (ClosedSpot, Vec<InstanceWorks>);

/// Generate data as defined by config
/// Consists from two parts: instance entries + sections for every instance
async fn generate_data(ora_sql: &config::ora_sql::Config, _environment: &Env) -> Result<String> {
    // TODO: detect instances
    // TODO: apply to config detected instances
    // TODO: customize instances
    // TODO: resulting in the list of endpoints

    let all = calc_spots(vec![ora_sql.endpoint()]);
    let connected = connect_spots(all, None);

    let mut _output = String::new();
    let sections = ora_sql
        .product()
        .sections()
        .iter()
        .map(|s| {
            let s = Section::new(s, ora_sql.product().cache_age());
            println!("{:?}", s.to_plain_header());
            s
        })
        .collect::<Vec<_>>();
    let works = connected
        .into_iter()
        .map(|spot| {
            let instances = WorkInstances::new(&spot);
            let closed = spot.close();

            let instance_works = instances
                .all()
                .keys()
                .map(|instance| {
                    let version = instances
                        .get_num_version(instance)
                        .ok()
                        .flatten()
                        .unwrap_or_default();
                    let queries = sections
                        .iter()
                        .filter_map(|section| {
                            _find_section_query(
                                section,
                                version,
                                Separator::Decorated(section.sep()),
                            )
                            .map(|q| (q, section.to_work_header()))
                        })
                        .collect::<Vec<(SqlQuery, String)>>();
                    (instance.clone(), queries)
                })
                .collect::<Vec<InstanceWorks>>();
            (closed, instance_works)
        })
        .collect::<Vec<SpotWorks>>();

    for (spot, instance_works) in works {
        log::info!("Processing spot: {:?}", spot.target());
        for (instance, queries) in instance_works {
            let r = spot.clone().connect(Some(&instance));
            match r {
                Ok(conn) => {
                    log::info!("Connected to instance: {}", instance);
                    for (query, title) in queries {
                        log::info!(
                            "Executing query for instance {}: {}",
                            instance,
                            query.as_str()
                        );
                        // Here you would execute the query and process the results
                        // For now, we just log it as a placeholder
                        println!("{title}");
                        conn.query(&query, "")
                            .unwrap_or_else(|e| {
                                log::error!(
                                    "Failed to execute query for instance {}: {}",
                                    instance,
                                    e
                                );
                                vec![e.to_string()]
                            })
                            .into_iter()
                            .for_each(|row| {
                                println!("{row}");
                            });
                    }
                }
                Err(e) => {
                    log::error!("Failed to connect to instance {}: {}", instance, e);
                    continue; // Skip this instance if connection fails
                }
            }
        }
    }

    Ok("".to_string())
}

fn _find_section_query(section: &Section, version: u32, sep: Separator) -> Option<SqlQuery> {
    let section_name = section.name();
    log::info!("Generating data for instance: {}", section_name);

    section.find_query(get_sql_dir(), version).map_or_else(
        || {
            log::warn!("No query found for section: {}", section_name);
            None
        },
        |query| {
            log::info!("Found query for section {}: {}", section_name, query);
            // Here you would execute the query and process the results
            // For now, we just return the query as a placeholder
            Some(SqlQuery::new(query.as_str(), sep))
        },
    )
}

// tested only in integration tests
fn connect_spots(spots: Vec<ClosedSpot>, instance: Option<&InstanceName>) -> Vec<OpenedSpot> {
    let connected = spots
        .into_iter()
        .filter_map(|t| match t.connect(instance) {
            Ok(opened) => {
                log::info!("Connected to instance: {:?}", &opened.target());
                Some(opened)
            }
            Err(e) => {
                log::error!("Error connecting to instance: {}", e);
                None
            }
        })
        .collect::<Vec<OpenedSpot>>();
    log::info!(
        "CONNECTED SPOTS: {:?}",
        connected.iter().map(|t| t.target()).collect::<Vec<_>>()
    );

    connected
}

fn calc_spots(endpoints: Vec<config::ora_sql::Endpoint>) -> Vec<ClosedSpot> {
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
        .collect::<Vec<ClosedSpot>>()
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
