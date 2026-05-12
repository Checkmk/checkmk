<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import { attributeTypePrefix, operatorPhrase, pillLabel } from './pill-label'
import type { AttributeCondition } from './types'

const props = defineProps<{
  condition: AttributeCondition
  ariaLabel?: string | undefined
}>()

const fullLabel = computed(() => pillLabel(props.condition))
const attributeTypeText = computed(() => attributeTypePrefix(props.condition.attributeType).trim())
const operatorText = computed(() => operatorPhrase(props.condition.operator))
const isExistence = computed(
  () => props.condition.operator === 'exists' || props.condition.operator === 'not_exists'
)
</script>

<template>
  <span
    class="metric-backend-attribute-filter-pill"
    :aria-label="ariaLabel ?? fullLabel"
    role="group"
  >
    <span class="metric-backend-attribute-filter-pill__segment" :title="fullLabel">
      <span
        v-if="condition.attributeType !== null"
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--attribute-type"
        >{{ attributeTypeText }}</span
      >
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--key"
        >{{ condition.key }}</span
      >
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--operator"
        >{{ operatorText }}</span
      >
      <span
        v-if="!isExistence"
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--value"
        >{{ condition.value }}</span
      >
    </span>
  </span>
</template>

<style scoped>
.metric-backend-attribute-filter-pill {
  background: var(--ux-theme-3);
  border: 1px solid var(--ux-theme-4);
  padding-right: var(--dimension-3);
  white-space: nowrap;
}

.metric-backend-attribute-filter-pill__segment {
  padding: var(--dimension-2) var(--dimension-3);
}

/* Attribute-type prefix and operator render as dimmed/italic metadata around key/value. */
.metric-backend-attribute-filter-pill__segment--attribute-type,
.metric-backend-attribute-filter-pill__segment--operator {
  color: var(--font-color-dimmed);
  font-style: italic;
}
</style>
