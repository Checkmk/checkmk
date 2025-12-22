<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'

import type { TagFilterConfig } from '../types.ts'

interface TagMatchItem {
  group: string | null
  operator: string
  value: string | null
}

interface Props {
  component: TagFilterConfig
  modelValue: TagMatchItem[]
}

const { _t } = usei18n()

const props = defineProps<Props>()

const operatorDisplayMap: Record<string, string> = {
  is: untranslated('='),
  isnot: untranslated('≠')
}

const displayRows = computed(() => {
  return props.modelValue.filter(
    (item) =>
      (item.group !== null && item.group !== '') ||
      (item.value !== null && item.value !== '') ||
      (item.operator && item.operator !== 'is')
  )
})

const hasData = computed(() => displayRows.value.length > 0)
</script>

<template>
  <div class="readonly-tag-filter-container">
    <div v-if="!hasData" class="empty-state">
      <CmkLabel>{{ _t('No tag filters configured') }}</CmkLabel>
    </div>
    <div v-else class="tag-filter-display">
      <div v-for="(item, index) in displayRows" :key="index" class="tag-filter-item">
        <CmkLabel>{{ item.group || '—' }}</CmkLabel>
        <CmkLabel>{{ operatorDisplayMap[item.operator] || item.operator }}</CmkLabel>
        <CmkLabel>{{ item.value || '—' }}</CmkLabel>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.readonly-tag-filter-container {
  display: flex;
  flex-direction: column;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.empty-state {
  padding: var(--dimension-2, 8px);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.tag-filter-display {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.tag-filter-item {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-1) 0;
}
</style>
