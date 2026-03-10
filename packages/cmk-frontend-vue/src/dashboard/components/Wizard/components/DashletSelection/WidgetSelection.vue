<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import SectionBlock from '@/dashboard/components/Wizard/components/SectionBlock.vue'

import WidgetItem from './WidgetItem.vue'

const { _t } = usei18n()

interface WidgetSelectionProps {
  availableItems: string[]
  enabledWidgets: string[]
}

const props = defineProps<WidgetSelectionProps>()
const selectedWidget = defineModel<string | null>('selectedWidget')
const isGraphEnabled = (graphName: string): boolean => {
  return props.enabledWidgets.includes(graphName)
}

const updateWidgetSelection = (graph: string) => {
  selectedWidget.value = graph
}
</script>

<template>
  <SectionBlock
    :title="_t('Choose how to display your data')"
    :subtitle="_t('Visualization types')"
  >
    <div class="db-widget-selection__container">
      <WidgetItem
        v-for="graph in availableItems"
        :key="graph"
        :name="graph"
        :selected="graph === selectedWidget"
        :enabled="isGraphEnabled(graph)"
        @update="updateWidgetSelection"
      />
    </div>
  </SectionBlock>
</template>

<style scoped>
.db-widget-selection__container {
  display: flex;
  gap: var(--spacing);
  justify-content: space-around;
  align-items: stretch;
  flex-flow: row wrap;
}
</style>
