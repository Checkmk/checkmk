/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Map data for tests.
 *
 * Built on the same factories the SPA uses, so a fixture carries exactly the
 * defaults a server-sent object would and a case only spells out what it is
 * actually about.
 */
import type {
  AggregationNode,
  ConnectionConfig,
  FolderTreeNode,
  GroupMember,
  MapConfig,
  MapElement,
  ObjectState,
  TopologyNode
} from '@/maps/types/api'
import { newMapElement, newMapView, newObjectState } from '@/maps/utils/model'

/** The production view defaults, so a fixture and a created map agree. */
export { newMapView }

/** A configured monitoring connection, for the cases that count them. */
export function aConnection(id: string, label = id): ConnectionConfig {
  return {
    id,
    type: 'livestatus',
    label,
    socket_path: null,
    host: null,
    port: null,
    timeout: 10,
    tls: true,
    tls_verify: true,
    checkmk_url: null,
    automation_user: null,
    automation_secret: null
  }
}

export function aMap(overrides: Partial<MapConfig> = {}): MapConfig {
  return {
    name: 'test',
    alias: 'Test',
    connection_id: 'live_1',
    icon_size: 30,
    rotation_interval: 0,
    sort_order: 0,
    click_action: 'link',
    render_mode: 'default',
    default_z: 1,
    show_in_lists: true,
    readonly: false,
    version: 0,
    view: newMapView('static'),
    objects: [],
    ...overrides
  }
}

export function anObject(
  overrides: Partial<MapElement> & Pick<MapElement, 'id' | 'type'>
): MapElement {
  return newMapElement(overrides)
}

export function aState(
  overrides: Partial<ObjectState> & Pick<ObjectState, 'object_id' | 'type' | 'state'>
): ObjectState {
  return newObjectState(overrides)
}

export function aFolderNode(
  overrides: Partial<FolderTreeNode> & Pick<FolderTreeNode, 'path'>
): FolderTreeNode {
  return {
    title: '',
    kind: 'folder',
    state: 'OK',
    is_empty: false,
    folder_id: '',
    host_count: 0,
    problem_count: 0,
    severity_counts: {},
    output: '',
    acknowledged: false,
    in_downtime: false,
    is_flapping: false,
    stale: false,
    site_id: null,
    children: [],
    ...overrides
  }
}

export function aTopologyNode(
  overrides: Partial<TopologyNode> & Pick<TopologyNode, 'name'>
): TopologyNode {
  return {
    parents: [],
    state: 'UP',
    output: '',
    services: [],
    acknowledged: false,
    in_downtime: false,
    notifications_enabled: true,
    active_checks_enabled: true,
    services_truncated_count: 0,
    services_omitted: false,
    alias: '',
    address: '',
    state_type: '',
    current_attempt: 0,
    max_attempts: 0,
    site_id: null,
    last_check: null,
    next_check: null,
    last_state_change: null,
    services_summary: null,
    ...overrides
  }
}

export function anAggregationNode(
  overrides: Partial<AggregationNode> & Pick<AggregationNode, 'name' | 'node_type'>
): AggregationNode {
  return {
    state: 0,
    output: '',
    acknowledged: false,
    in_downtime: false,
    children: [],
    ...overrides
  }
}

export function aGroupMember(
  overrides: Partial<GroupMember> & Pick<GroupMember, 'host'>
): GroupMember {
  return {
    service: '',
    state: 'OK',
    output: '',
    acknowledged: false,
    in_downtime: false,
    notifications_enabled: true,
    last_state_change: null,
    ...overrides
  }
}
