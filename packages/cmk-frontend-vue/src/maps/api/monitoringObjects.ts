/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What the operator can bind a map object to: hosts, services, groups, folders,
 * sites, BI aggregations.
 *
 * All of it is resolved by the GUI, not the daemon — these run inside a Checkmk
 * request with the caller's own permissions, which is what makes an
 * auth-scoped ``sites.live()`` (and, for BI, Checkmk's own BIManager) available.
 * They ride the GUI session, so no ticket is involved.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type {
  AggregationInfo,
  AggregationNode,
  AggregationStateRaw,
  GroupMember,
  PerfMetricsSource
} from '@/maps/types/api'

export class MonitoringObjectsApi {
  public async fetchFolders(): Promise<{ path: string; title: string }[]> {
    return unwrap(await client.GET('/domain-types/maps_folder/collections/all')).folders
  }

  public async fetchSites(): Promise<{ id: string; alias: string }[]> {
    return unwrap(await client.GET('/domain-types/maps_site/collections/all')).sites
  }

  public async fetchAggregations(): Promise<AggregationInfo[]> {
    return unwrap(await client.GET('/domain-types/maps_aggregation/collections/all')).aggregations
  }

  /**
   * A POST on a read: an aggregation name is free-form text and the state poll
   * sends a whole batch of them, which is too long and too structured for a query
   * string.
   */
  public async fetchAggregationTree(
    aggregationId: string,
    depth: number
  ): Promise<{ tree: AggregationNode | null; connection_ok: boolean }> {
    return unwrap(
      await client.POST('/domain-types/maps_aggregation/actions/show-tree/invoke', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { aggregation_id: aggregationId, depth }
      })
    )
  }

  public async fetchAggregationStates(
    aggregationIds: string[]
  ): Promise<Record<string, AggregationStateRaw>> {
    return unwrap(
      await client.POST('/domain-types/maps_aggregation/actions/show-states/invoke', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { aggregation_ids: aggregationIds }
      })
    ).states
  }

  public async fetchGroupMembers(
    groupType: 'hostgroup' | 'servicegroup',
    groupName: string
  ): Promise<GroupMember[]> {
    return unwrap(
      await client.GET('/domain-types/maps_member/collections/group', {
        params: { query: { group_type: groupType, group_name: groupName } }
      })
    ).members
  }

  public async fetchDyngroupMembers(
    objectTypes: 'host' | 'service',
    objectFilter: string
  ): Promise<GroupMember[]> {
    return unwrap(
      await client.GET('/domain-types/maps_member/collections/dyngroup', {
        params: { query: { object_types: objectTypes, object_filter: objectFilter } }
      })
    ).members
  }

  /**
   * An object's raw perfdata. Titles, units and applicable graphs are display
   * semantics and come from {@link MetricInfoApi} instead.
   */
  public async fetchPerfMetrics(host: string, service?: string): Promise<PerfMetricsSource> {
    return unwrap(
      await client.GET('/domain-types/maps_perf_metrics/collections/all', {
        params: { query: { host_name: host, ...(service && { service_description: service }) } }
      })
    )
  }

  /** On-demand geo lookup for one host, for a worldmap that places hosts itself. */
  public async fetchHostGeo(host: string): Promise<{ lat: number; lng: number } | null> {
    return unwrap(
      await client.GET('/objects/maps_host_geo/{host_name}', {
        params: { path: { host_name: host } }
      })
    ).geo
  }
}
