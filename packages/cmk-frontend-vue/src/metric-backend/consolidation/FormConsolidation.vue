<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import InlineEditPill from '../InlineEditPill.vue'
import { compactFunction } from './consolidation-label'
import type { ConsolidationModel } from './types'

const model = defineModel<ConsolidationModel>({ required: true })

const typeToken = computed(() => `[${model.value.type}]`)
const functionToken = computed(() => compactFunction(model.value))
const lookbackToken = computed(() => `${model.value.lookbackSeconds}s`)
</script>

<template>
  <InlineEditPill
    :tab-focusable="false"
    scope-marker-attr="data-consolidation-scope"
    item-marker-attr="data-consolidation-item"
  >
    <template #read-only>
      <span
        class="metric-backend-form-consolidation__segment metric-backend-form-consolidation__segment--dimmed"
        >{{ typeToken }}</span
      >
      <span class="metric-backend-form-consolidation__segment">{{ functionToken }}</span>
      <span class="metric-backend-form-consolidation__segment">{{ lookbackToken }}</span>
    </template>
  </InlineEditPill>
</template>

<style scoped>
.metric-backend-form-consolidation__segment {
  padding: var(--dimension-2) var(--dimension-3);
  display: inline-flex;
  align-items: center;
}

.metric-backend-form-consolidation__segment--dimmed {
  color: var(--font-color-dimmed);
  font-style: italic;
}
</style>
