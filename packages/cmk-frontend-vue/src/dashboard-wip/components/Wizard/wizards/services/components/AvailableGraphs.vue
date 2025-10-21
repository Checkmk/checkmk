<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { SimpleIcons } from '@/components/CmkIcon'

import WidgetButton from '@/dashboard-wip/components/Wizard/components/WidgetButton.vue'

import { Graph } from '../composables/useSelectGraphTypes'

const { _t } = usei18n()

type GraphEntry = {
  id: Graph
  label: TranslatedString
  icon: SimpleIcons
}

type GraphDirectory = GraphEntry[]

interface AvaliableGraphsProps {
  availableGraphs: Graph[]
}

const props = defineProps<AvaliableGraphsProps>()

const graphDirectory: GraphDirectory = [
  { id: Graph.SERVICE_STATE, label: _t('Service state'), icon: 'graph' },
  { id: Graph.SERVICE_STATE_SUMMARY, label: _t('Service state summary'), icon: 'gauge' },
  { id: Graph.SERVICE_STATISTICS, label: _t('Service statistics'), icon: 'single-metric' }
]
</script>

<template>
  <div class="db-available-graphs__container">
    <WidgetButton
      v-for="(graph, index) in graphDirectory"
      :key="index"
      class="db-available-graphs__item"
      :icon="graph.icon"
      :label="graph.label"
      :disabled="!props.availableGraphs.includes(graph.id)"
    />
  </div>
</template>

<style scoped>
.db-available-graphs__container {
  display: flex;
  flex-flow: row wrap;
  gap: 8px;
  place-content: space-around center;
  align-items: stretch;
}

.db-available-graphs__container-item-disabled {
  text-decoration: line-through;
  background-color: var(--color-dark-red-60) !important;
}

.db-available-graphs__item {
  /* Base styles for all items */
  padding: 12px;
  border-radius: 6px;
  text-align: center;
}
</style>
