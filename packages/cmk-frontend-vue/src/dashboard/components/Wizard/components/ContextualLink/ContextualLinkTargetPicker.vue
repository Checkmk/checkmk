<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMenu, { type CmkMenuCategory, type CmkMenuItem } from 'cmk-ui-library/components/CmkMenu'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { VisualLocation } from './contextualLink'
import { type LinkTarget, linkTargetTitle } from './useLinkTargets'

const { _t } = usei18n()

const target = defineModel<VisualLocation | null>({ required: true })

const { targets, viewsError, dashboardsError } = defineProps<{
  targets: LinkTarget[]
  viewsError: string | null
  dashboardsError: string | null
}>()

const categories = computed<CmkMenuCategory[]>(() => [
  { value: 'dashboards', title: _t('Dashboard') },
  { value: 'views', title: _t('View') }
])

function itemValue({ type, name }: VisualLocation): string {
  return `${type}:${name}`
}

// The name tells apart targets of the same title, and lets search find a target by it.
const items = computed<CmkMenuItem[]>(() =>
  targets.map((linkTarget) => ({
    label: [
      { text: linkTarget.title, truncateOrder: 2 },
      { text: linkTarget.name, truncateOrder: 1 }
    ],
    value: itemValue(linkTarget),
    category: linkTarget.type,
    detail: linkTarget.isBuiltIn ? _t('Built-in') : _t('Custom')
  }))
)

const selectedTitle = computed(() =>
  target.value === null ? undefined : linkTargetTitle(targets, target.value)
)

function select(value: string): void {
  const linkTarget = targets.find((candidate) => itemValue(candidate) === value)
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
