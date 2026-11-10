<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMenu, { type CmkMenuCategory, type CmkMenuItem } from 'cmk-ui-library/components/CmkMenu'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref } from 'vue'

import { useViewsCollection } from '@/dashboard/composables/api/useViewsCollection'

import { type DashboardTarget, fetchDashboardTargets } from '../WidgetVisualization/api'
import type { VisualLocation } from './contextualLink'

interface LinkTarget extends VisualLocation {
  title: string
  isBuiltIn: boolean
}

const { _t } = usei18n()

const target = defineModel<VisualLocation | null>({ required: true })

const { list: views, ensureLoaded: ensureViewsLoaded, error: viewsError } = useViewsCollection()
const dashboards = ref<DashboardTarget[]>([])
const dashboardsError = ref<string | null>(null)

onMounted(async () => {
  try {
    dashboards.value = await fetchDashboardTargets()
  } catch (error: unknown) {
    dashboardsError.value = String(error)
  }
})
onMounted(ensureViewsLoaded)

const categories = computed<CmkMenuCategory[]>(() => [
  { value: 'dashboards', title: _t('Dashboard') },
  { value: 'views', title: _t('View') }
])

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

function itemValue({ type, name }: VisualLocation): string {
  return `${type}:${name}`
}

// The name tells apart targets of the same title, and lets search find a target by it.
const items = computed<CmkMenuItem[]>(() =>
  targets.value.map((linkTarget) => ({
    label: [
      { text: linkTarget.title, truncateOrder: 2 },
      { text: linkTarget.name, truncateOrder: 1 }
    ],
    value: itemValue(linkTarget),
    category: linkTarget.type,
    detail: linkTarget.isBuiltIn ? _t('Built-in') : _t('Custom')
  }))
)

// A stored target that is no longer listed keeps its name.
const selectedTitle = computed(() => {
  if (target.value === null) {
    return undefined
  }
  const { type, name } = target.value
  return (
    targets.value.find((linkTarget) => linkTarget.type === type && linkTarget.name === name)
      ?.title ?? name
  )
})

function select(value: string): void {
  const linkTarget = targets.value.find((candidate) => itemValue(candidate) === value)
  if (linkTarget !== undefined) {
    target.value = { type: linkTarget.type, name: linkTarget.name }
  }
}
</script>

<template>
  <div v-if="dashboardsError" class="error-message">
    {{ _t('Error loading dashboards: ') + dashboardsError }}
  </div>
  <div v-if="viewsError" class="error-message">
    {{ _t('Error loading views: ') + viewsError }}
  </div>
  <CmkMenu
    :items="items"
    :categories="categories"
    :label="_t('Target page')"
    trigger-variant="field"
    :trigger-text="selectedTitle"
    :search-placeholder="_t('Search target pages ...')"
    searchable
    @select="select"
  />
</template>
