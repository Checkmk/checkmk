// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self, OracleConfig};
use crate::ora_sql::backend::{make_spot, ClosedSpot, OpenedSpot};
use crate::ora_sql::custom::get_sql_dir;
use crate::ora_sql::section::Section;
use crate::ora_sql::system::WorkInstances;
use crate::setup::Env;
use crate::types::{InstanceName, InstanceNumVersion, Separator, SqlBindParam, SqlQuery, Tenant};
use crate::utils;

use crate::config::defines::defaults::DEFAULT_SEP;
use anyhow::Result;

impl OracleConfig {
    pub async fn exec(&self, environment: &Env) -> Result<String> {
        if let Some(ora_sql) = self.ora_sql() {
            OracleConfig::prepare_cache_sub_dir(environment, &ora_sql.config_cache_dir());
            log::info!("Generating main data");
            let mut output: Vec<String> = Vec::new();
            output.extend(
                generate_data(ora_sql, environment)
                    .await
                    .unwrap_or_else(|e| {
                        log::error!("Error generating data at main config: {e}");
                        vec![format!("{e}\n")]
                    }),
            );
            for (num, config) in std::iter::zip(0.., ora_sql.configs()) {
                log::info!("Generating configs data");
                OracleConfig::prepare_cache_sub_dir(environment, &config.config_cache_dir());
                let configs_data = generate_data(config, environment)
                    .await
                    .unwrap_or_else(|e| {
                        log::error!("Error generating data at config {num}: {e}");
                        vec![format!("{e}\n")]
                    });
                output.extend(configs_data);
            }
            Ok(output.join("\n"))
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
async fn generate_data(
    ora_sql: &config::ora_sql::Config,
    environment: &Env,
) -> Result<Vec<String>> {
    // TODO: detect instances
    // TODO: apply to config detected instances
    // TODO: customize instances
    // TODO: resulting in the list of endpoints

    let all = calc_spots(vec![ora_sql.endpoint()]);
    let connected = connect_spots(all, None);

    let sections = ora_sql
        .product()
        .sections()
        .iter()
        .filter_map(|s| {
            if !s.is_allowed(environment.execution()) {
                log::info!(
                    "Skip section: {:?} not allowed in {:?}",
                    s,
                    environment.execution()
                );
                return None;
            }
            let s = Section::new(s, ora_sql.product().cache_age());
            Some(s)
        })
        .collect::<Vec<_>>();
    let mut output: Vec<String> = sections
        .iter()
        .filter_map(|s| s.to_signaling_header())
        .collect();
    let works = make_spot_works(connected, sections, ora_sql.params());
    output.extend(process_spot_works(works));
    Ok(output)
}

fn make_spot_works(
    spots: Vec<OpenedSpot>,
    sections: Vec<Section>,
    params: &[SqlBindParam],
) -> Vec<SpotWorks> {
    spots
        .into_iter()
        .map(|spot| {
            let instances = WorkInstances::new(&spot, None);
            let closed = spot.close();
            let instance_works = instances
                .all()
                .keys()
                .filter_map(|instance| {
                    if let Some(info) = instances.get_info(instance) {
                        Some((instance, info))
                    } else {
                        log::warn!("No info found for instance: {}", instance);
                        None
                    }
                })
                .map(|(instance, info)| {
                    let queries = sections
                        .iter()
                        .filter_map(|section| {
                            if !instance.is_suitable_affinity(section.affinity()) {
                                log::info!(
                                    "Skip section with not suitable affinity: {:?} instance {}",
                                    section,
                                    instance
                                );
                                return None;
                            }
                            _find_section_query(
                                section,
                                info.0,
                                info.1,
                                Separator::Decorated(section.sep()),
                                params,
                            )
                            .map(|q| (q, section.to_work_header()))
                        })
                        .collect::<Vec<(SqlQuery, String)>>();
                    (instance.clone(), queries)
                })
                .collect::<Vec<InstanceWorks>>();
            (closed, instance_works)
        })
        .collect::<Vec<SpotWorks>>()
}

fn process_spot_works(works: Vec<SpotWorks>) -> Vec<String> {
    works
        .into_iter()
        .flat_map(|(spot, instance_works)| {
            log::info!("Spot: {:?}", spot.target());
            instance_works
                .iter()
                .flat_map(|(instance, queries)| {
                    log::info!("Instance: {}", instance);
                    queries.iter().map(|(query, title)| {
                        log::info!("Query: {}", title);
                        let results =
                            _exec_queries(&spot, instance, &[(query.clone(), title.clone())]);
                        results.join("\n")
                    })
                })
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>()
}

fn _exec_queries(
    spot: &ClosedSpot,
    instance: &InstanceName,
    queries: &[(SqlQuery, String)],
) -> Vec<String> {
    let r = spot.clone().connect(Some(instance));
    match r {
        Ok(conn) => {
            log::info!("Connected to : {}", instance);
            queries
                .iter()
                .flat_map(|(query, title)| {
                    log::info!("Executing query: {}", query.as_str());
                    let mut result = conn
                        .query_table(query)
                        .format(&DEFAULT_SEP.to_string())
                        .unwrap_or_else(|e| {
                            log::error!("Failed to execute query for instance {}: {}", instance, e);
                            vec![e.to_string()]
                        });
                    result.insert(0, title.clone());
                    result
                })
                .collect::<Vec<_>>()
        }
        Err(e) => {
            log::error!("Failed to connect to instance {}: {}", instance, e);
            vec![] // Skip this instance if connection fails
        }
    }
}
fn _find_section_query(
    section: &Section,
    version: InstanceNumVersion,
    tenant: Tenant,
    sep: Separator,
    params: &[SqlBindParam],
) -> Option<SqlQuery> {
    let section_name = section.name();
    log::info!("Generating data for instance: {}", section_name);

    section
        .find_query(get_sql_dir(), version, tenant)
        .map_or_else(
            || {
                log::warn!(
                    "No query found for section: {} {} {:?}",
                    section_name,
                    version,
                    tenant
                );
                None
            },
            |query| {
                log::info!("Found query for section {}: {}", section_name, query);
                // Here you would execute the query and process the results
                // For now, we just return the query as a placeholder
                Some(SqlQuery::new(query.as_str(), sep, params))
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
