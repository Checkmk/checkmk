<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

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
  <CmkHeading type="h3">{{ _t('Choose how to display your data') }}</CmkHeading>
  <div class="widget-selection__container">
    <WidgetItem
      v-for="graph in availableItems"
      :key="graph"
      :name="graph"
      :selected="graph === selectedWidget"
      :enabled="isGraphEnabled(graph)"
      @update="updateWidgetSelection"
    />
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.widget-selection__container {
  display: flex;
  gap: var(--spacing);
  justify-content: space-around;
  align-items: stretch;
  flex-flow: row wrap;
}
</style>
