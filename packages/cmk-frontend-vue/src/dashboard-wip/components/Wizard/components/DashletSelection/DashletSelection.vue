<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import DashletItem from './DashletItem.vue'

const { _t } = usei18n()

interface DashletSelectionProps {
  availableItems: string[]
  enabledDashlets: string[]
}

const props = defineProps<DashletSelectionProps>()
const selectedDashlet = defineModel<string | null>('selectedDashlet')
const isGraphEnabled = (graphName: string): boolean => {
  return props.enabledDashlets.includes(graphName)
}

const updateDashletSelection = (graph: string) => {
  selectedDashlet.value = graph
}
</script>

<template>
  <CmkHeading type="h3">{{ _t('Choose how to display your data') }}</CmkHeading>
  <div class="dashlet-selection__container">
    <DashletItem
      v-for="graph in availableItems"
      :key="graph"
      :name="graph"
      :selected="graph === selectedDashlet"
      :enabled="isGraphEnabled(graph)"
      @update="updateDashletSelection"
    />
  </div>
</template>

<style scoped>
.dashlet-selection__container {
  display: flex;
  gap: var(--spacing);
  justify-content: space-around;
  align-items: stretch;
  flex-flow: row wrap;
}
</style>
