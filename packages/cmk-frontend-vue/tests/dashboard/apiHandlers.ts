/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { restApiHttp, type useMswServer } from 'cmk-ui-library/vitest.msw'
import { afterEach, beforeEach, expect, vi } from 'vitest'

import type { ViewModel } from '@/dashboard/types/api'
import type { DashboardMainMenuTopic, DashboardMetadata } from '@/dashboard/types/dashboard'

/** Answers the title request of a widget wizard preview, which shows the widget under the title. */
export function widgetTitlesHandler(title: string) {
  return restApiHttp.post(
    '/domain-types/dashboard/actions/compute-widget-titles/invoke',
    ({ response }) =>
      response(200).json({
        domainType: 'dashboard-widget-titles',
        id: 'titles',
        links: [],
        extensions: { titles: { preview_widget: title } }
      })
  )
}

/** Answers the attributes request of a widget wizard preview with a widget that uses no infos. */
export function widgetAttributesHandler() {
  return restApiHttp.post(
    '/domain-types/dashboard/actions/compute-widget-attributes/invoke',
    ({ response }) =>
      response(200).json({
        domainType: 'widget-compute',
        value: { filter_context: { uses_infos: [] } }
      })
  )
}

/** The metadata of an anchored dashboard, built-in unless it has an owner. */
export function dashboardMetadata(
  name: string,
  title: string,
  owner: string | null
): DashboardMetadata {
  return {
    name,
    owner,
    is_built_in: owner === null,
    is_editable: false,
    layout_type: 'relative_grid',
    restricted_to_single: [],
    display: {
      title,
      topic: { name: 'overview', breadcrumb: [] },
      hidden: false,
      sort_index: 99,
      hide_in_drop_down_menus: false
    }
  }
}

function dashboardMetadataObject(
  extensions: DashboardMetadata
): components['schemas']['DashboardMetadataModel'] {
  return {
    domainType: 'dashboard_metadata',
    id: extensions.name,
    title: extensions.display.title,
    links: [],
    extensions
  }
}

function dashboardMetadataCollection(
  dashboards: DashboardMetadata[]
): components['schemas']['DashboardMetadataCollectionModel'] {
  return {
    domainType: 'dashboard_metadata',
    id: 'all',
    links: [],
    value: dashboards.map(dashboardMetadataObject)
  }
}

/** Serves the metadata list only to the list requests with the given all-owners flag. */
export function dashboardMetadataListHandler(
  dashboards: DashboardMetadata[],
  { allOwners }: { allOwners: boolean }
) {
  return restApiHttp.get(
    '/domain-types/dashboard_metadata/collections/all',
    ({ query, response }) =>
      (query.get('all_owners') === 'true') === allOwners
        ? response(200).json(dashboardMetadataCollection(dashboards))
        : undefined
  )
}

/** Serves the metadata list for all owners, and a known dashboard by name and owner. */
export function dashboardMetadataHandlers(dashboards: DashboardMetadata[]) {
  return [
    dashboardMetadataListHandler(dashboards, { allOwners: true }),
    restApiHttp.get('/objects/dashboard_metadata/{dashboard_id}', ({ params, query, response }) => {
      const owner = query.get('owner')
      const extensions = dashboards.find(
        (dashboard) => dashboard.name === params.dashboard_id && (dashboard.owner ?? '') === owner
      )
      return extensions === undefined
        ? undefined
        : response(200).json(dashboardMetadataObject(extensions))
    })
  ]
}

/** Serves the views. */
export function viewsHandler(views: ViewModel[]) {
  return restApiHttp.get('/domain-types/view/collections/all', ({ response }) =>
    response(200).json({ domainType: 'view', id: 'all', links: [], value: views })
  )
}

/** Serves the topics of the main menu. */
export function mainMenuTopicsHandler(topics: DashboardMainMenuTopic[]) {
  return restApiHttp.get('/domain-types/pagetype_topic/collections/all', ({ response }) =>
    response(200).json({
      domainType: 'pagetype_topic',
      id: 'all',
      links: [],
      value: topics.map((topic) => ({
        domainType: 'pagetype_topic',
        id: topic.id,
        title: topic.title,
        links: [],
        extensions: { sort_index: topic.sortIndex, is_default: topic.isDefault, description: '' }
      }))
    })
  )
}

/** Waits after each test until every request that the test started has an answer. */
export function useAnsweredRequestsAfterEach(server: ReturnType<typeof useMswServer>): void {
  const unanswered = new Map<string, string>()
  server.events.on('request:start', ({ request, requestId }) => {
    unanswered.set(requestId, `${request.method} ${new URL(request.url).pathname}`)
  })
  server.events.on('request:end', ({ requestId }) => {
    unanswered.delete(requestId)
  })
  beforeEach(() => {
    unanswered.clear()
  })
  afterEach(() => vi.waitFor(() => expect([...unanswered.values()]).toEqual([])))
}

/** A list of request records that is empty at the start of each test. */
export function useRequestRecords<T>(): T[] {
  const records: T[] = []
  beforeEach(() => {
    records.length = 0
  })
  return records
}
