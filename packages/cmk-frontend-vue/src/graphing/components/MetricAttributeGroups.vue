<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { type MetricAttribute, attributeGroupTitle, groupedAttributes } from './metricAttributes'

const props = defineProps<{
  attributes: MetricAttribute[]
}>()

const groups = computed(() => groupedAttributes(props.attributes))
</script>

<template>
  <div class="graphing-metric-attribute-groups">
    <div v-for="group in groups" :key="group.kind" class="graphing-metric-attribute-groups__group">
      <div class="graphing-metric-attribute-groups__title">
        {{ attributeGroupTitle(group.kind) }}
      </div>
      <div
        v-for="attribute in group.attributes"
        :key="attribute.name"
        class="graphing-metric-attribute-groups__attribute"
      >
        <span class="graphing-metric-attribute-groups__name">{{ attribute.name }}</span>
        <span class="graphing-metric-attribute-groups__value">{{ attribute.value }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.graphing-metric-attribute-groups {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
  font-size: var(--font-size-normal);
}

.graphing-metric-attribute-groups__title {
  font-weight: var(--font-weight-bold);
}

/* Fixed fractions, so names and values line up across groups. */
.graphing-metric-attribute-groups__attribute {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
  gap: var(--spacing-half);
}

.graphing-metric-attribute-groups__name,
.graphing-metric-attribute-groups__value {
  overflow-wrap: anywhere;
}
</style>
