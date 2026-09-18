<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCollapsible, { CmkCollapsibleTitle } from 'cmk-ui-library/components/CmkCollapsible'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

import MetricAttributesTable from '../../components/MetricAttributesTable.vue'
import type { Metric } from '../../components/TimeSeriesGraph'
import { withNameToggled } from '../../components/legend/legendUtils'
import { attributesOf, hasAttributes } from '../../components/metricAttributes'
import { orderMetricsTopToBottom } from '../../components/metricOrder'

const { metrics } = defineProps<{
  metrics: Metric[]
}>()

const emit = defineEmits<{
  hoverMetrics: [names: string[]]
}>()

const { _t } = usei18n()
const componentId = useId()

const open = ref(true)
const expandedNames = ref<string[]>([])

const lines = computed(() => orderMetricsTopToBottom([...metrics]))

function toggleAttributes(name: string): void {
  expandedNames.value = withNameToggled(expandedNames.value, name)
}

/** Guards an expanded line whose series came back without attributes. */
function showsAttributes(metric: Metric): boolean {
  return hasAttributes(metric) && expandedNames.value.includes(metric.metadata.name)
}

function attributesId(name: string): string {
  return `${componentId}-attributes-${name}`
}
</script>

<template>
  <div class="graphing-metrics-preview">
    <CmkCollapsibleTitle :title="_t('Metrics preview')" :open="open" @toggle-open="open = !open" />
    <CmkCollapsible :open="open">
      <table class="graphing-metrics-preview__table">
        <tbody>
          <template v-for="line in lines" :key="line.metadata.name">
            <tr
              @mouseenter="emit('hoverMetrics', [line.metadata.name])"
              @mouseleave="emit('hoverMetrics', [])"
            >
              <td class="graphing-metrics-preview__swatch-cell">
                <span
                  class="graphing-metrics-preview__swatch"
                  :style="{ background: line.metadata.color }"
                />
              </td>
              <td class="graphing-metrics-preview__name">
                <span class="graphing-metrics-preview__title" :title="line.metadata.title">
                  {{ line.metadata.title }}
                </span>
                <CmkIconButton
                  v-if="hasAttributes(line)"
                  class="graphing-metrics-preview__attributes-toggle"
                  :name="showsAttributes(line) ? 'chevron-up' : 'chevron-down'"
                  primary-color="font"
                  size="small"
                  :aria-expanded="showsAttributes(line)"
                  :aria-controls="attributesId(line.metadata.name)"
                  :aria-label="
                    _t('Toggle attributes of %{metric}', { metric: line.metadata.title })
                  "
                  @click="toggleAttributes(line.metadata.name)"
                />
              </td>
            </tr>
            <!-- Kept in the hovered series' region: the attributes describe that one line. -->
            <tr
              v-if="showsAttributes(line)"
              @mouseenter="emit('hoverMetrics', [line.metadata.name])"
              @mouseleave="emit('hoverMetrics', [])"
            >
              <td />
              <td
                :id="attributesId(line.metadata.name)"
                class="graphing-metrics-preview__attributes"
              >
                <MetricAttributesTable :attributes="attributesOf(line)" />
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </CmkCollapsible>
  </div>
</template>

<style scoped>
.graphing-metrics-preview__table {
  border-collapse: collapse;
  width: 100%;
  margin-top: var(--dimension-4);
}

.graphing-metrics-preview__swatch-cell {
  width: var(--dimension-8);
  padding-left: var(--dimension-5);
  vertical-align: top;
}

.graphing-metrics-preview__swatch {
  display: inline-block;
  width: var(--dimension-6);
  height: var(--dimension-6);
  border-radius: var(--border-radius);
}

.graphing-metrics-preview__name {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 0;
}

.graphing-metrics-preview__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.graphing-metrics-preview__attributes {
  padding: var(--dimension-3) 0 var(--dimension-5) 0;
}
</style>
