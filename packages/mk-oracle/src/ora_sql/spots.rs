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

use crate::config::ora_sql::CustomInstance;
use crate::ora_sql::backend::{ClosedSpot, OpenedSpot};
use crate::ora_sql::pdbs::{resolve_pdb_patterns, Pdbs};
use crate::ora_sql::section::Section;
use crate::ora_sql::system::WorkInstances;
use crate::types::{InstanceName, PdbName, SqlBindParam, SqlQuery};

use anyhow::Result;

/// Controls how SQL result rows are rendered into agent output.
///
/// `Passthrough` is used for custom-metric blocks: each SELECT-ed cell is
/// emitted as-is, with no column-separator rewriting.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PostProcessing {
    Standard,
    Passthrough,
}

/// One block of queries to execute for a section, along with the agent
/// header(s) that precede the rows and a flag controlling output formatting.
#[derive(Debug, Clone)]
pub struct QueryBlock {
    pub queries: Vec<SqlQuery>,
    pub title: String,
    pub post_processing: PostProcessing,
    pub container: Option<PdbName>,
}

type InstanceWorks = (InstanceName, Vec<QueryBlock>);
type OpenedSpotWorkResults = (OpenedSpot, Result<Vec<InstanceWorks>>);
pub type OpenedSpotWorks = (OpenedSpot, Vec<InstanceWorks>);
pub type ClosedSpotWorks = (ClosedSpot, Vec<InstanceWorks>);

type SpotErrors = (ClosedSpot, anyhow::Error);

pub fn make_spot_work_results(
    spots: Vec<OpenedSpot>,
    sections: Vec<Section>,
    custom_instances: &[CustomInstance],
    global_cache_age: u32,
    params: &[SqlBindParam],
) -> (Vec<OpenedSpotWorks>, Vec<SpotErrors>) {
    let work_results = spots
        .into_iter()
        .map(|opened| {
            let instance_candidates = WorkInstances::new(&opened, None);
            match instance_candidates {
                Err(ref e) => _make_work_result_error(opened, e),
                Ok(mut instances) => {
                    if let Err(e) = instances.discover_pdbs(&opened) {
                        log::warn!("PDB discovery failed for {:?}: {e}", opened.target());
                    }
                    let pdbs = instances.pdbs().clone();
                    let merged_sections = merge_per_instance_sections(
                        &sections,
                        &opened,
                        custom_instances,
                        global_cache_age,
                    );
                    _make_work_result_ok(opened, instances, &merged_sections, params, &pdbs)
                }
            }
        })
        .collect::<Vec<OpenedSpotWorkResults>>();

    work_results.into_iter().fold(
        (Vec::new(), Vec::new()),
        |(mut ok, mut err), (closed, res)| {
            match res {
                Ok(instance_works) => ok.push((closed, instance_works)),
                Err(e) => err.push((closed.close(), e)),
            }
            (ok, err)
        },
    )
}

/// Merge the global section list with per-instance `custom_metrics` of the
/// `CustomInstance` whose target matches this spot. Per-instance entries
/// override global entries that share the same `item_value` (per tech design:
/// "If a global and a per-instance query share the same item_name, the
/// per-instance one wins.").
fn merge_per_instance_sections(
    global: &[Section],
    spot: &OpenedSpot,
    custom_instances: &[CustomInstance],
    global_cache_age: u32,
) -> Vec<Section> {
    let spot_target_id = spot.target().target_id();
    let per_instance_runtime: Vec<Section> = custom_instances
        .iter()
        .find(|custom_instance| custom_instance.target_id() == spot_target_id)
        .map(|custom_instance| {
            custom_instance
                .custom_metrics()
                .iter()
                .map(|cs| Section::new(cs, global_cache_age))
                .collect()
        })
        .unwrap_or_default();

    if per_instance_runtime.is_empty() {
        return global.to_vec();
    }
    let overridden_items: std::collections::HashSet<&str> = per_instance_runtime
        .iter()
        .filter_map(|s| s.item_value().map(|v| v.as_str()))
        .collect();

    let mut merged: Vec<Section> = global
        .iter()
        .filter(|s| {
            s.item_value()
                .map(|v| !overridden_items.contains(v.as_str()))
                .unwrap_or(true)
        })
        .cloned()
        .collect();
    merged.extend(per_instance_runtime);
    merged
}

fn _make_work_result_error(opened: OpenedSpot, e: &anyhow::Error) -> OpenedSpotWorkResults {
    let target = opened.target().clone();
    log::error!("Failed to get instances for spot {:?}: {}", target, e);
    (
        opened,
        Err(anyhow::anyhow!(
            "REMOTE_INSTANCE_{}|FAILURE|WARNING: {} ",
            target.display_name(),
            e.to_string().replace("OCI Error: ", "")
        )),
    )
}

fn _make_work_result_ok(
    opened: OpenedSpot,
    instances: WorkInstances,
    sections: &[Section],
    params: &[SqlBindParam],
    pdbs: &Pdbs,
) -> OpenedSpotWorkResults {
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
        .map(|(service, info)| {
            let queries = sections
                .iter()
                .filter_map(|section| {
                    if !service.is_suitable_affinity(section.affinity()) {
                        log::info!(
                            "Skip section with not suitable affinity: {:?} instance {}",
                            section,
                            service
                        );
                        return None;
                    }
                    section
                        .find_queries(info.0, info.1, params)
                        .map(|q| (section, q))
                })
                .flat_map(|(section, q)| {
                    let post = if section.item_value().is_some() {
                        PostProcessing::Passthrough
                    } else {
                        PostProcessing::Standard
                    };
                    if section.pdb_patterns().is_empty() {
                        vec![QueryBlock {
                            queries: q,
                            title: section.to_work_header_for(service),
                            post_processing: post,
                            container: None,
                        }]
                    } else {
                        resolve_pdb_patterns(section.pdb_patterns(), pdbs)
                            .into_iter()
                            .map(|pdb| QueryBlock {
                                queries: q.clone(),
                                title: section.to_work_header_for_pdb(service, &pdb),
                                post_processing: post,
                                container: Some(pdb),
                            })
                            .collect()
                    }
                })
                .collect::<Vec<QueryBlock>>();
            (service.clone(), queries)
        })
        .collect::<Vec<InstanceWorks>>();
    (opened, Ok(instance_works))
}
