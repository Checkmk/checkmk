<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import InlineEditPill from '../InlineEditPill.vue'
import { clauseSummary } from './group-by-label'
import type { GroupByModel } from './types'

const { _t } = usei18n()

defineProps<{
  ariaLabel?: string | undefined
}>()

const model = defineModel<GroupByModel>({ required: true })

const summary = computed(() => clauseSummary(model.value))
const editAriaLabel = computed(() => `${_t('Edit group by')}: ${summary.value}`)

const editing = ref(false)
</script>

<template>
  <InlineEditPill
    :editing="editing"
    :tab-focusable="false"
    :aria-label="ariaLabel ?? summary"
    :edit-aria-label="editAriaLabel"
    scope-marker-attr="data-gb-scope"
    item-marker-attr="data-gb-item"
    @edit="editing = true"
    @done="editing = false"
  >
    <template #read-only>
      <span class="metric-backend-form-group-by__summary">{{ summary }}</span>
    </template>
    <template #edit>
      <!-- Mirrors the summary until the editable controls arrive in a later slice. -->
      <span class="metric-backend-form-group-by__summary">{{ summary }}</span>
    </template>
  </InlineEditPill>
</template>

<style scoped>
.metric-backend-form-group-by__summary {
  padding: var(--dimension-2) var(--dimension-3);
  display: inline-flex;
  align-items: center;
}
</style>
