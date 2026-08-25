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

use crate::config::options::Options;
use crate::config::ora_sql::CustomInstance;
use crate::config::target::TargetId;
use crate::ora_sql::backend::{sanitize_failure_message, ClosedSpot, OpenedSpot};
use crate::ora_sql::pdbs::{resolve_pdb_patterns, Pdbs};
use crate::ora_sql::section::Section;
use crate::ora_sql::system::WorkInstances;
use crate::types::{InstanceName, PdbName, SectionName, SqlBindParam, SqlQuery};

use anyhow::Result;
use std::collections::HashSet;

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
    excluded_sections: &[(TargetId, Vec<SectionName>)],
    global_cache_age: Option<u32>,
    params: &[SqlBindParam],
    options: &Options,
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
                        excluded_sections,
                        global_cache_age,
                        options,
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
    global_sections: &[Section],
    spot: &OpenedSpot,
    custom_instances: &[CustomInstance],
    excluded_sections: &[(TargetId, Vec<SectionName>)],
    global_cache_age: Option<u32>,
    options: &Options,
) -> Vec<Section> {
    let spot_target_id = spot.target().target_id();
    let Some(instance) = custom_instances
        .iter()
        .find(|custom_instance| custom_instance.target_id() == spot_target_id)
    else {
        // A spot without an `instances:` entry comes from the main endpoint, i.e.
        // from the deprecated main-level `connection.sid`. Neither its custom
        // metrics nor its `excluded_sections` are honoured: main-level targets
        // are on the way out and get the global sections unchanged.
        return global_sections.to_vec();
    };

    let custom_sections: Vec<Section> = instance
        .custom_metrics()
        .iter()
        .map(|cs| Section::new(cs, global_cache_age, options))
        .collect();

    let mut merged = drop_overridden(global_sections, &item_names(&custom_sections));
    merged.extend(custom_sections);
    // Matched case-insensitively: yaml upper-cases a sid and an instance_name by
    // itself, but keeps the case of a service_name or an alias.
    if let Some(sections) = instance.target_id().and_then(|target_id| {
        excluded_sections
            .iter()
            .find(|(target, _)| target.eq_ignore_case(target_id))
            .map(|(_, sections)| sections)
    }) {
        merged.retain(|s| {
            let excluded = sections.contains(s.name());
            if excluded {
                log::debug!(
                    "Skip section {} excluded for {:?}",
                    s.name(),
                    instance.target_id()
                );
            }
            !excluded
        });
    }
    merged
}

/// Item names of the given sections. Only custom metrics can have an item name.
fn item_names(sections: &[Section]) -> HashSet<&str> {
    sections
        .iter()
        .filter_map(|s| s.item_value().map(|v| v.as_str()))
        .collect()
}

/// Copy of `global_sections` without the custom metrics whose item name is in
/// `overriding_items`. Predefined sections carry no item name and always stay.
fn drop_overridden(global_sections: &[Section], overriding_items: &HashSet<&str>) -> Vec<Section> {
    global_sections
        .iter()
        .filter(|s| {
            s.item_value()
                .map(|v| !overriding_items.contains(v.as_str()))
                .unwrap_or(true)
        })
        .cloned()
        .collect()
}

fn _make_work_result_error(opened: OpenedSpot, e: &anyhow::Error) -> OpenedSpotWorkResults {
    let target = opened.target().clone();
    log::error!("Failed to get instances for spot {:?}: {}", target, e);
    (
        opened,
        Err(anyhow::anyhow!(
            "{}|FAILURE|WARNING: {} ",
            target.display_name(),
            sanitize_failure_message(&e.to_string())
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
                        resolve_pdb_patterns(section.pdb_patterns(), pdbs, &service.to_string())
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ora_sql::Config;
    use crate::config::section::SectionBuilder;
    use crate::ora_sql::backend::test_support::{open_spot, MiniOra};
    use crate::types::ItemValue;

    const MERGE_YAML: &str = r#"
oracle:
  main:
    authentication:
      username: u
      password: p
      type: standard
    connection:
      hostname: localhost
    discovery:
      detect: no
    custom_metrics:
      - shared:
          sql: "select 'details:g-shared' from dual"
      - global_only:
          sql: "select 'details:g-only' from dual"
    instances:
      - service_name: ORCL2
        custom_metrics:
          - shared:
              sql: "select 'details:i-shared' from dual"
          - instance_only:
              sql: "select 'details:i-only' from dual"
"#;

    fn config_from(yaml: &str) -> Config {
        Config::from_string(yaml).unwrap().unwrap()
    }

    /// Runtime custom-metric sections built from the global `custom_metrics:`.
    fn global_sections(config: &Config) -> Vec<Section> {
        config
            .product()
            .sections()
            .iter()
            .filter(|s| s.is_custom_metric())
            .map(|s| Section::new(s, Some(0), config.options()))
            .collect()
    }

    /// Sorted item names of the sections (custom metrics carry an item value).
    fn custom_item_names(sections: &[Section]) -> Vec<String> {
        let mut names: Vec<String> = sections
            .iter()
            .filter_map(|s| s.item_value().map(|v| v.as_str().to_string()))
            .collect();
        names.sort();
        names
    }

    // TC-ORA-102 (Param: per-instance + global merge): adds to global, overrides on collision.
    #[test]
    fn test_merge_per_instance_adds_and_overrides_by_item_name() {
        let config = config_from(MERGE_YAML);
        let global = global_sections(&config);
        let instances = config.instances().clone();
        // A spot whose target_id mirrors the configured ORCL2 instance.
        let spot = open_spot(MiniOra::single("ORCL2"), Some(&instances[0]));

        let merged =
            merge_per_instance_sections(&global, &spot, &instances, &[], Some(0), config.options());

        // global_only (kept) + shared (folded, not duplicated) + instance_only (added)
        assert_eq!(
            custom_item_names(&merged),
            vec!["global_only", "instance_only", "shared"]
        );
        // The surviving `shared` is the per-instance definition (it won the collision).
        let shared = merged
            .iter()
            .find(|s| s.item_value().map(|v| v.as_str()) == Some("shared"))
            .expect("shared metric present");
        assert_eq!(
            shared.inline_sql(),
            Some("select 'details:i-shared' from dual")
        );
    }

    // TC-ORA-102 (Param: no matching per-instance metrics): global unchanged.
    #[test]
    fn test_merge_per_instance_without_customs_returns_global() {
        let config = config_from(MERGE_YAML);
        let global = global_sections(&config);
        // No custom instance is passed, so nothing matches the spot's target.
        let spot = open_spot(MiniOra::single("ORCLX"), None);

        let merged =
            merge_per_instance_sections(&global, &spot, &[], &[], Some(0), config.options());

        assert_eq!(custom_item_names(&merged), custom_item_names(&global));
    }

    /// Sorted names of the sections: item name for custom metrics, section name otherwise.
    fn section_names(sections: &[Section]) -> Vec<String> {
        let mut names: Vec<String> = sections
            .iter()
            .map(|s| {
                s.item_value()
                    .map(|v| v.as_str())
                    .unwrap_or_else(|| s.name().as_str())
                    .to_string()
            })
            .collect();
        names.sort();
        names
    }

    fn predefined(name: &str) -> Section {
        Section::new(
            &SectionBuilder::new(name).build(),
            Some(0),
            &Options::default(),
        )
    }

    fn custom_metric(item: &str) -> Section {
        Section::new(
            &SectionBuilder::new(item)
                .set_item_value(ItemValue::from(item.to_string()))
                .build(),
            Some(0),
            &Options::default(),
        )
    }

    #[test]
    fn test_item_names_collects_custom_metrics_only() {
        let sections = vec![predefined("sessions"), custom_metric("price")];
        assert_eq!(item_names(&sections), HashSet::from(["price"]));
    }

    #[test]
    fn test_drop_overridden_removes_named_metrics_only() {
        let sections = vec![
            predefined("sessions"),
            custom_metric("price"),
            custom_metric("keep"),
        ];

        let kept = drop_overridden(&sections, &HashSet::from(["price"]));

        assert_eq!(section_names(&kept), vec!["keep", "sessions"]);
    }

    /// An exclusion naming a bare `service_name` must not hit an instance whose
    /// `instance_name` happens to carry that name: the targets differ.
    #[test]
    fn test_excluded_sections_do_not_match_a_same_named_other_target() {
        const YAML: &str = r#"
oracle:
  main:
    authentication:
      username: u
      password: p
      type: standard
    discovery:
      detect: no
    excluded_sections:
      - target_id:
          service_name: PROD
        sections: [jobs]
    instances:
      - service_name: other_service
        instance_name: PROD
"#;
        let config = config_from(YAML);
        let global: Vec<Section> = config
            .product()
            .sections()
            .iter()
            .map(|s| Section::new(s, Some(0), config.options()))
            .collect();
        let instances = config.instances().clone();
        let spot = open_spot(MiniOra::single("PROD"), Some(&instances[0]));

        let merged = merge_per_instance_sections(
            &global,
            &spot,
            &instances,
            config.excluded_sections(),
            Some(0),
            config.options(),
        );

        assert_eq!(section_names(&merged), section_names(&global));
    }

    /// An exclusion is scoped to its target: another instance keeps everything.
    #[test]
    fn test_excluded_sections_leave_other_instances_alone() {
        const YAML: &str = r#"
oracle:
  main:
    authentication:
      username: u
      password: p
      type: standard
    discovery:
      detect: no
    excluded_sections:
      - target_id:
          sid: A
        sections: [jobs]
    instances:
      - sid: A
      - sid: B
"#;
        let config = config_from(YAML);
        let global: Vec<Section> = config
            .product()
            .sections()
            .iter()
            .map(|s| Section::new(s, Some(0), config.options()))
            .collect();
        let instances = config.instances().clone();
        let merge = |instance| {
            merge_per_instance_sections(
                &global,
                &open_spot(MiniOra::single("ANY"), Some(instance)),
                &instances,
                config.excluded_sections(),
                Some(0),
                config.options(),
            )
        };

        assert!(!section_names(&merge(&instances[0])).contains(&"jobs".to_string()));
        assert_eq!(section_names(&merge(&instances[1])), section_names(&global));
    }

    /// The whole key is matched case-insensitively: `X:Z:V` == `x:z:v`. Yaml
    /// upper-cases a sid and an instance_name by itself, but leaves a
    /// `service_name` and an `alias` as written, so the lookup folds case.
    #[test]
    fn test_excluded_sections_matched_by_target_id() {
        const YAML: &str = r#"
oracle:
  main:
    authentication:
      username: u
      password: p
      type: standard
    discovery:
      detect: no
    excluded_sections:
      - target_id:
          service_name: Prod_Service
          sid: Xe
        sections: [jobs]
    instances:
      - service_name: prod_service
        sid: xe
"#;
        let config = config_from(YAML);
        let global: Vec<Section> = config
            .product()
            .sections()
            .iter()
            .map(|s| Section::new(s, Some(0), config.options()))
            .collect();
        let instances = config.instances().clone();
        let spot = open_spot(MiniOra::single("XE"), Some(&instances[0]));

        let merged = merge_per_instance_sections(
            &global,
            &spot,
            &instances,
            config.excluded_sections(),
            Some(0),
            config.options(),
        );

        let kept = section_names(&merged);
        assert!(!kept.contains(&"jobs".to_string()), "{kept:?}");
        assert_eq!(kept.len(), global.len() - 1, "{kept:?}");
    }

    #[test]
    fn test_drop_overridden_without_names_keeps_everything() {
        let sections = vec![predefined("sessions"), custom_metric("price")];

        let kept = drop_overridden(&sections, &HashSet::new());

        assert_eq!(section_names(&kept), section_names(&sections));
    }
}
