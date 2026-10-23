<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import type { Section, Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref } from 'vue'

import { listCustomGraphMetadata } from '../api'

export interface SelectableGraph {
  name: string
  owner: string
  title: string
}

const { selected, loggedInUser } = defineProps<{
  selected: SelectableGraph | null
  loggedInUser: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  'graph-change': [graph: SelectableGraph]
}>()

const { _t } = usei18n()

const graphs = ref<SelectableGraph[]>(selected ? [selected] : [])

const byTitle = (a: SelectableGraph, b: SelectableGraph): number => a.title.localeCompare(b.title)

const graphKey = (graph: SelectableGraph): string => `${graph.owner}/${graph.name}`

const options = computed<Suggestions>(() => {
  const own = graphs.value.filter((graph) => graph.owner === loggedInUser).sort(byTitle)
  const published = graphs.value.filter((graph) => graph.owner !== loggedInUser).sort(byTitle)
  const sections: Section[] = []
  if (own.length > 0) {
    sections.push({
      title: _t('My custom graphs'),
      suggestions: own.map((graph) => ({ name: graphKey(graph), title: untranslated(graph.title) }))
    })
  }
  if (published.length > 0) {
    sections.push({
      title: _t('Published custom graphs'),
      suggestions: published.map((graph) => ({
        name: graphKey(graph),
        title: untranslated(`${graph.title} (${graph.owner})`)
      }))
    })
  }
  return { type: 'filtered', suggestions: sections }
})

const selectedKey = computed<string | null>(() => (selected ? graphKey(selected) : null))

function onSelect(key: string | null): void {
  const graph = graphs.value.find((candidate) => graphKey(candidate) === key)
  if (graph) {
    emit('graph-change', graph)
  }
}

const fetchFailed = ref(false)

const noElementsText = computed(() =>
  fetchFailed.value ? _t('Failed to load the custom graphs') : _t('No custom graphs found')
)

async function fetchGraphs(): Promise<void> {
  try {
    const collection = await listCustomGraphMetadata()
    graphs.value = collection.value.flatMap((entry) =>
      entry.id === undefined
        ? []
        : [{ name: entry.id, owner: entry.extensions.owner, title: entry.title ?? entry.id }]
    )
  } catch {
    fetchFailed.value = true
    graphs.value = []
  }
}

onMounted(() => {
  void fetchGraphs()
})
</script>

<template>
  <div class="graphing-graph-selector">
    <CmkDropdown
      :model-value="selectedKey"
      :options="options"
      :label="_t('Select custom graph')"
      :input-hint="_t('Select custom graph')"
      :no-elements-text="noElementsText"
      :no-results-hint="noElementsText"
      :disabled="disabled"
      width="fill"
      floating
      @update:model-value="onSelect"
    />
  </div>
</template>

<style scoped>
.graphing-graph-selector {
  min-width: 200px;
  max-width: 240px;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.graphing-graph-selector :deep(.cmk-dropdown-button) {
  height: var(--dimension-10);
  align-items: center;
  padding-top: 0;
  padding-bottom: 0;
  border: var(--dimension-1) solid var(--default-form-element-border-color);
  border-radius: var(--dimension-3);
}
</style>
