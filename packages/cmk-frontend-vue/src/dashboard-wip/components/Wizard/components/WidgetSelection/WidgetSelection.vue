<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import { Graph } from '../../wizards/metrics/composables/useSelectGraphTypes'
import WidgetButton from '../WidgetButton.vue'

const { _t } = usei18n()

interface WidgetSelectionProps {
  availableItems: string[]
  enabledWidgets: string[]
}

defineProps<WidgetSelectionProps>()
const selectedWidget = defineModel<string | null>('selectedWidget')

const updateWidgetSelection = (graph: string) => {
  selectedWidget.value = graph
}
</script>

<template>
  <CmkHeading type="h3">{{ _t('Choose how to display your data') }}</CmkHeading>
  <div class="widget-selection__container">
    <WidgetButton
      icon="graph"
      :label="_t('Graph')"
      :selected="selectedWidget === Graph.SINGLE_GRAPH"
      @click="() => updateWidgetSelection(Graph.SINGLE_GRAPH)"
    />

    <WidgetButton
      icon="single-metric"
      :label="_t('Metric')"
      :selected="selectedWidget === Graph.SINGLE_METRIC"
      @click="() => updateWidgetSelection(Graph.SINGLE_METRIC)"
    />

    <WidgetButton
      icon="gauge"
      :label="_t('Gauge')"
      :selected="selectedWidget === Graph.GAUGE"
      @click="() => updateWidgetSelection(Graph.GAUGE)"
    />
  </div>
  <div class="widget-selection__container">
    <WidgetButton
      icon="barplot"
      :label="_t('Barplot')"
      :selected="selectedWidget === Graph.BARPLOT"
      @click="() => updateWidgetSelection(Graph.BARPLOT)"
    />

    <WidgetButton
      icon="scatterplot"
      :label="_t('Scatterplot')"
      :selected="selectedWidget === Graph.SCATTERPLOT"
      @click="() => updateWidgetSelection(Graph.SCATTERPLOT)"
    />

    <WidgetButton
      icon="top-list"
      :label="_t('Top list')"
      :selected="selectedWidget === Graph.TOP_LIST"
      @click="() => updateWidgetSelection(Graph.TOP_LIST)"
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
