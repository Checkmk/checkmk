<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import type { QuerySuggestionsFn } from '@/components/CmkSuggestions/types'

import AttributeFilterPill from './AttributeFilterPill.vue'
import type { AttributeFilterModel, ConnectedCondition } from './types'

const { _t } = usei18n()

defineProps<{
  querySuggestions: QuerySuggestionsFn
  ariaLabel?: string | undefined
}>()

const model = defineModel<AttributeFilterModel>({ default: () => [] })

function removeCondition(target: ConnectedCondition): void {
  model.value = model.value.filter((c) => c !== target)
}

function updateKey(target: ConnectedCondition, value: string | null): void {
  model.value = model.value.map((c) => (c === target ? { ...c, key: value } : c))
}
</script>

<template>
  <div role="group" :aria-label="ariaLabel ?? _t('Attribute filter')">
    <AttributeFilterPill
      v-for="entry in model"
      :key="entry.id"
      :condition="entry"
      :query-suggestions="querySuggestions"
      removable
      @remove="removeCondition(entry)"
      @update:key="(value) => updateKey(entry, value)"
    />
  </div>
</template>
