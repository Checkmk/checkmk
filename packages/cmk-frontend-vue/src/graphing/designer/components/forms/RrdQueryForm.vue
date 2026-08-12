<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Section, Suggestion, Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import {
  type ConfiguredFilters,
  type ConfiguredValues,
  type FilterType,
  getCategoryDefinition,
  parseFilterTypes,
  useFilterDefinitions,
  useFilterGroups,
  useFilters
} from 'cmk-ui-library/components/filter'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { ConsolidationFn } from '@/graphing/components/consolidation'

import type { GraphItemsStore } from '../../composables/useGraphItems'
import type { DraftRRDQueryItem } from '../../drafts'
import FilterQuerySection from './FilterQuerySection.vue'
import ConsolidationSelect from './fields/ConsolidationSelect.vue'
import ServiceMetricSelect from './fields/ServiceMetricSelect.vue'

type Category = 'host' | 'service'

const { item, store, metricNameErrors } = defineProps<{
  item: DraftRRDQueryItem
  store: GraphItemsStore
  metricNameErrors: TranslatedString[]
}>()

const { _t } = usei18n()

const filterDefinitions = useFilterDefinitions()
const filterGroups = useFilterGroups()

// The filter state is the editing-session source of truth; changes are cloned back into the
// item's `context` (the persisted `VisualContext`) via `syncContext`.
const filters = useFilters(JSON.parse(JSON.stringify(item.context)) as ConfiguredFilters)

const filterCategories = parseFilterTypes(filterDefinitions, new Set<string>(['host', 'service']))

function activeIdsFor(category: Category): string[] {
  return filters.activeFilters.value.filter(
    (id) => filterDefinitions[id]?.extensions.info === category
  )
}
const hostActiveIds = computed(() => activeIdsFor('host'))
const serviceActiveIds = computed(() => activeIdsFor('service'))

function toSuggestion(filterType: FilterType): Suggestion {
  return { name: filterType.id, title: untranslated(filterType.title) }
}

const byTitle = (a: { title: string }, b: { title: string }): number =>
  a.title.localeCompare(b.title, undefined, { sensitivity: 'base' })

/** Grouped, filterable options for the add-dropdown, excluding already-active filters. */
function addSuggestionsFor(category: Category): Suggestions {
  const active = new Set(filters.activeFilters.value)
  const available = (filterCategories.get(category) ?? []).filter((f) => !active.has(f.id))

  const standalone: FilterType[] = []
  const groups = new Map<string, FilterType[]>()
  for (const filterType of available) {
    if (filterType.group === null) {
      standalone.push(filterType)
    } else {
      const entries = groups.get(filterType.group) ?? []
      entries.push(filterType)
      groups.set(filterType.group, entries)
    }
  }

  const sections: Section[] = []
  if (standalone.length > 0) {
    sections.push({
      title: untranslated(getCategoryDefinition(category).title),
      suggestions: [...standalone].sort(byTitle).map(toSuggestion)
    })
  }
  sections.push(
    ...[...groups.entries()]
      .map(([groupId, entries]) => ({
        title: untranslated(filterGroups[groupId]?.title || groupId),
        suggestions: [...entries].sort(byTitle).map(toSuggestion)
      }))
      .sort(byTitle)
  )

  return { type: 'filtered', suggestions: sections }
}
const hostSuggestions = computed(() => addSuggestionsFor('host'))
const serviceSuggestions = computed(() => addSuggestionsFor('service'))

function syncContext(): void {
  store.replace({
    ...item,
    context: JSON.parse(JSON.stringify(filters.getFilters())) as ConfiguredFilters
  })
}

function onAddFilter(filterId: string): void {
  filters.addFilter(filterId)
}

function onUpdateFilter(filterId: string, values: ConfiguredValues): void {
  filters.updateFilterValues(filterId, values)
  syncContext()
}

function onRemoveFilter(filterId: string): void {
  filters.removeFilter(filterId)
  syncContext()
}

function onMetricChange(metricName: string | null): void {
  store.replace({ ...item, metric_name: metricName })
}

function onConsolidationChange(value: ConsolidationFn): void {
  store.replace({ ...item, consolidation: value })
}
</script>

<template>
  <div class="graphing-rrd-query-form">
    <FilterQuerySection
      :title="_t('Host filter')"
      :add-label="_t('Add host filter')"
      :active-filter-ids="hostActiveIds"
      :get-filter-values="filters.getFilterValues"
      :add-suggestions="hostSuggestions"
      :filter-definitions="filterDefinitions"
      @add-filter="onAddFilter"
      @update-filter="onUpdateFilter"
      @remove-filter="onRemoveFilter"
    />
    <FilterQuerySection
      :title="_t('Service filter')"
      :add-label="_t('Add service filter')"
      :active-filter-ids="serviceActiveIds"
      :get-filter-values="filters.getFilterValues"
      :add-suggestions="serviceSuggestions"
      :filter-definitions="filterDefinitions"
      @add-filter="onAddFilter"
      @update-filter="onUpdateFilter"
      @remove-filter="onRemoveFilter"
    />
    <ServiceMetricSelect
      :model-value="item.metric_name"
      :context="item.context"
      :placeholder="_t('Select service metric')"
      required
      show-independent-of-context
      :errors="metricNameErrors"
      @update:model-value="onMetricChange"
    />
    <ConsolidationSelect
      :model-value="item.consolidation"
      @update:model-value="onConsolidationChange"
    />
  </div>
</template>

<style scoped>
.graphing-rrd-query-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}
</style>
