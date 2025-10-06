<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import WidgetButton from '../../../components/WidgetButton.vue'
import { Graph } from '../composables/useSelectGraphTypes'

const { _t } = usei18n()

interface WidgetSelectionProps {
  availableItems: string[]
  enabledWidgets: string[]
}

defineProps<WidgetSelectionProps>()
const selectedWidget = defineModel<string>('selectedWidget', { required: true })

const updateWidgetSelection = (graph: string) => {
  selectedWidget.value = graph
}
</script>

<template>
  <CmkHeading type="h3">{{ _t('Choose how to display your data') }}</CmkHeading>
  <div class="db-widget-selection__container">
    <WidgetButton
      icon="graph"
      :label="_t('Service state')"
      :selected="selectedWidget === Graph.SERVICE_STATE"
      @click="() => updateWidgetSelection(Graph.SERVICE_STATE)"
    />

    <WidgetButton
      icon="graph"
      :label="_t('Service state summary')"
      :selected="selectedWidget === Graph.SERVICE_STATE_SUMMARY"
      @click="() => updateWidgetSelection(Graph.SERVICE_STATE_SUMMARY)"
    />
  </div>
  <div class="db-widget-selection__container">
    <WidgetButton
      icon="graph"
      :label="_t('Service statistics')"
      :selected="selectedWidget === Graph.SERVICE_STATISTICS"
      @click="() => updateWidgetSelection(Graph.SERVICE_STATISTICS)"
    />
  </div>
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
