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

use crate::ora_sql::backend::{ClosedSpot, OpenedSpot};
use crate::ora_sql::custom::get_sql_dir;
use crate::ora_sql::section::Section;
use crate::ora_sql::system::WorkInstances;
use crate::types::{InstanceName, SqlBindParam, SqlQuery};

use anyhow::Result;

type InstanceWorks = (InstanceName, Vec<(Vec<SqlQuery>, String)>);
type SpotWorkResults = (ClosedSpot, Result<Vec<InstanceWorks>>);
pub type SpotWorks = (ClosedSpot, Vec<InstanceWorks>);
type SpotErrors = (ClosedSpot, anyhow::Error);

pub fn make_spot_work_results(
    spots: Vec<OpenedSpot>,
    sections: Vec<Section>,
    params: &[SqlBindParam],
) -> (Vec<SpotWorks>, Vec<SpotErrors>) {
    let work_results = spots
        .into_iter()
        .map(|spot| {
            let instance_candidates = WorkInstances::new(&spot, None);
            let closed = spot.close();
            match instance_candidates {
                Err(ref e) => _make_closed_error(closed, e),
                Ok(instances) => _make_closed_ok(closed, instances, &sections, params),
            }
        })
        .collect::<Vec<SpotWorkResults>>();

    work_results.into_iter().fold(
        (Vec::new(), Vec::new()),
        |(mut ok, mut err), (closed, res)| {
            match res {
                Ok(instance_works) => ok.push((closed, instance_works)),
                Err(e) => err.push((closed, e)),
            }
            (ok, err)
        },
    )
}

fn _make_closed_error(closed: ClosedSpot, e: &anyhow::Error) -> SpotWorkResults {
    let target = closed.target().clone();
    log::error!("Failed to get instances for spot {:?}: {}", target, e);
    (
        closed,
        Err(anyhow::anyhow!(
            "REMOTE_INSTANCE_{}|FAILURE|WARNING: {} ",
            target.display_name(),
            e.to_string().replace("OCI Error: ", "")
        )),
    )
}

fn _make_closed_ok(
    closed: ClosedSpot,
    instances: WorkInstances,
    sections: &[Section],
    params: &[SqlBindParam],
) -> SpotWorkResults {
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
                        .find_queries(get_sql_dir(), info.0, info.1, params)
                        .map(|q| (q, section.to_work_header()))
                })
                .collect::<Vec<(Vec<SqlQuery>, String)>>();
            (service.clone(), queries)
        })
        .collect::<Vec<InstanceWorks>>();
    (closed, Ok(instance_works))
}
