/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, ref } from 'vue'

import { useViewsCollection } from '@/dashboard/composables/api/useViewsCollection'

import { type DashboardTarget, fetchDashboardTargets } from '../WidgetVisualization/api'
import type { VisualLocation } from './contextualLink'

export interface LinkTarget extends VisualLocation {
  title: string
  isBuiltIn: boolean
}

export function linkTargetTitle(targets: LinkTarget[], { type, name }: VisualLocation): string {
  return (
    targets.find((linkTarget) => linkTarget.type === type && linkTarget.name === name)?.title ??
    name
  )
}

export function useLinkTargets() {
  const { list: views, ensureLoaded: ensureViewsLoaded, error: viewsError } = useViewsCollection()
  const dashboards = ref<DashboardTarget[]>([])
  const dashboardsError = ref<string | null>(null)
  let loaded = false

  async function loadDashboards(): Promise<void> {
    try {
      dashboards.value = await fetchDashboardTargets()
    } catch (error: unknown) {
      dashboardsError.value = String(error)
    }
  }

  async function load(): Promise<void> {
    if (loaded) {
      return
    }
    loaded = true
    await Promise.all([loadDashboards(), ensureViewsLoaded()])
  }

  const targets = computed<LinkTarget[]>(() =>
    [
      ...dashboards.value.map(({ name, title, isBuiltIn }) => ({
        type: 'dashboards' as const,
        name,
        title,
        isBuiltIn
      })),
      ...views.value.map((view) => ({
        type: 'views' as const,
        name: view.id!,
        title: view.title!,
        isBuiltIn: view.extensions.owner === ''
      }))
    ].sort((a, b) => a.title.localeCompare(b.title))
  )

  return { targets, viewsError, dashboardsError, load }
}
