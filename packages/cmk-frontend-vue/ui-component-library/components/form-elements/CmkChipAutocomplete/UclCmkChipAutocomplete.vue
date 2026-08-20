<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkChipAutocompleteCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['ArrowDown', 'ArrowUp'],
    description:
      'Move focus through the suggestions. The same model a column funnel uses, so mounting this inside one gives a single list to walk rather than two competing ones.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'Select the focused suggestion. It becomes a chip, the input clears and focus returns to it.'
  },
  {
    keys: ['Backspace'],
    description: 'With an empty input, remove the chip added last.'
  },
  {
    keys: ['Escape'],
    description:
      'Clear the typed text. The keypress stops there rather than reaching an enclosing popover, so a first Escape does not also close it.'
  }
]

export const panelConfig = {
  latency: {
    type: 'number' as const,
    title: 'Suggest latency (ms)',
    initialState: 300,
    help: 'Delay of the demo suggestion source, to show the debounce and the stale-response guard.'
  },
  suggestWhenEmpty: {
    type: 'boolean' as const,
    title: 'suggestWhenEmpty',
    initialState: false,
    help: 'Ask the callback with an empty query on focus, seeding the list before anything is typed.'
  },
  keyValue: {
    type: 'boolean' as const,
    title: 'keyValue',
    initialState: false,
    help: 'Pick key:value pairs in two steps. Picking a bare key continues the query as "key:" rather than committing a chip, and the callback is asked again for that key\'s values.'
  },
  wildcardOption: {
    type: 'boolean' as const,
    title: 'wildcardOption',
    initialState: false,
    help: 'Offer what was typed with a trailing * as the first entry, for everything starting with it.'
  },
  maxSelected: {
    type: 'number' as const,
    title: 'maxSelected',
    initialState: 0,
    help: 'Refuse further picks once this many are selected. 0 leaves it unbounded.'
  },
  placeholder: {
    type: 'string' as const,
    title: 'placeholder',
    initialState: 'Search',
    help: 'Placeholder of the search field. Defaults to "Search" when left empty.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import CmkChipAutocomplete from 'cmk-ui-library/components/CmkChipAutocomplete.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

const { screenshotMode } = defineProps<{ screenshotMode: boolean }>()

const DEMO_VALUES = [
  'cmk/check_mk_server:yes',
  'cmk/docker_object:container',
  'cmk/docker_object:node',
  'cmk/os_family:linux',
  'cmk/os_family:windows',
  'cmk/site:heute',
  'criticality:prod',
  'criticality:test',
  'networking:core',
  'networking:edge'
]

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const selected = ref<string[]>([])

const maxSelected = computed(() =>
  propState.value.maxSelected > 0 ? propState.value.maxSelected : undefined
)

const placeholder = computed(() =>
  propState.value.placeholder ? untranslated(propState.value.placeholder) : undefined
)

function matchesFor(query: string): string[] {
  const needle = query.trim().toLowerCase()
  return DEMO_VALUES.filter((value) => value.toLowerCase().includes(needle))
}

function suggest(query: string): Promise<string[]> {
  const matches = matchesFor(query)
  if (screenshotMode) {
    return Promise.resolve(matches)
  }
  return new Promise((resolve) => {
    setTimeout(() => resolve(matches), propState.value.latency)
  })
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkChipAutocomplete</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-chip-autocomplete__panel">
        <CmkChipAutocomplete
          v-model="selected"
          :suggest="suggest"
          :placeholder="placeholder"
          :suggest-when-empty="propState.suggestWhenEmpty"
          :key-value="propState.keyValue"
          :wildcard-option="propState.wildcardOption"
          :max-selected="maxSelected"
        />
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>

<style scoped>
/* Bounded the way a column funnel bounds it, which is where it is first used. */
.ucl-cmk-chip-autocomplete__panel {
  width: 280px;
  padding: var(--dimension-4);
  border: 1px solid var(--ux-theme-4);
  background: var(--ux-theme-2);
}
</style>
