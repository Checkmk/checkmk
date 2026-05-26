<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, nextTick, useTemplateRef, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'
import type { QuerySuggestionsFn } from '@/components/CmkSuggestions/types'

import { ATTRIBUTE_TYPE_LABELS, operatorPhrase, pillLabel } from './pill-label'
import type { AttributeCondition, AttributeType } from './types'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    condition: AttributeCondition
    querySuggestions: QuerySuggestionsFn
    ariaLabel?: string | undefined
    removable?: boolean
  }>(),
  { removable: false }
)

const emit = defineEmits<{
  (e: 'remove'): void
  (e: 'update:key', value: string): void
  (e: 'update:attributeType', value: AttributeType): void
}>()

const fullLabel = computed(() => pillLabel(props.condition))
const operatorText = computed(() => operatorPhrase(props.condition.operator))
const isExistence = computed(
  () => props.condition.operator === 'exists' || props.condition.operator === 'not_exists'
)

function onKeyUpdate(value: string | null): void {
  emit('update:key', value ?? '')
}

const attributeTypeInput = computed<string | null>({
  get: () => props.condition.attributeType,
  set: (value) => {
    const valid =
      value !== null && Object.hasOwn(ATTRIBUTE_TYPE_LABELS, value)
        ? (value as AttributeType)
        : null
    emit('update:attributeType', valid)
  }
})

const attributeTypeDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>(
  'attributeTypeDropdownRef'
)

// On a fresh key with no type yet, auto-open the type dropdown. Deferred to
// nextTick so the `:disabled` gate has re-rendered and the inferred type has
// propagated before we read it.
watch(
  () => props.condition.key,
  (next, prev) => {
    if (next === prev || next === '') {
      return
    }
    void nextTick(() => {
      if (props.condition.attributeType !== null) {
        return
      }
      attributeTypeDropdownRef.value?.open()
    })
  }
)

const attributeTypeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'resource', title: _t('Resource') },
    { name: 'scope', title: _t('Scope') },
    { name: 'datapoint', title: _t('Data point') }
  ]
}))
</script>

<template>
  <span
    class="metric-backend-attribute-filter-pill"
    :aria-label="ariaLabel ?? fullLabel"
    role="group"
  >
    <span class="metric-backend-attribute-filter-pill__segment" :title="fullLabel">
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--attribute-type"
      >
        <CmkDropdown
          ref="attributeTypeDropdownRef"
          v-model:selected-option="attributeTypeInput"
          :options="attributeTypeOptions"
          :disabled="!condition.key"
          :input-hint="_t('Attribute type')"
          :label="_t('Attribute type')"
        />
      </span>
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--key"
      >
        <CmkDropdown
          :selected-option="condition.key || null"
          :options="{ type: 'callback-filtered', querySuggestions }"
          :label="_t('Attribute key')"
          :input-hint="_t('Attribute key')"
          @update:selected-option="onKeyUpdate"
        />
      </span>
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
    <CmkIconButton
      v-if="removable"
      class="metric-backend-attribute-filter-pill__remove"
      name="close"
      size="small"
      :title="_t('Remove condition')"
      :aria-label="_t('Remove condition')"
      @mousedown.prevent
      @click.stop="emit('remove')"
    />
  </span>
</template>

<style scoped>
.metric-backend-attribute-filter-pill {
  display: inline-flex;
  align-items: stretch;
  background: var(--ux-theme-3);
  border: 1px solid var(--ux-theme-4);
  padding-right: var(--dimension-3);
  white-space: nowrap;
}

.metric-backend-attribute-filter-pill__segment {
  padding: var(--dimension-2) var(--dimension-3);
}

.metric-backend-attribute-filter-pill__remove {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--dimension-2);
}

/* Operator renders as dimmed/italic metadata around key/value. */
.metric-backend-attribute-filter-pill__segment--operator {
  color: var(--font-color-dimmed);
  font-style: italic;
}
</style>
