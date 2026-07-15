<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import type { QuerySuggestionsFn } from 'cmk-ui-library/components/CmkSuggestions/types'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import InlineEditPill from '../InlineEditPill.vue'
import { keyPillLabel, levelLabel } from './group-by-label'
import { GROUP_LEVELS, isKeyValid } from './types'
import type { GroupKey, GroupLevel } from './types'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    condition: GroupKey
    querySuggestions: QuerySuggestionsFn
    removable?: boolean
    editing?: boolean
    ariaLabel?: string | undefined
  }>(),
  {
    removable: false,
    editing: false,
    ariaLabel: undefined
  }
)

const emit = defineEmits<{
  (e: 'remove'): void
  (e: 'edit'): void
  (e: 'done'): void
  (e: 'update:level', value: GroupLevel): void
  (e: 'update:key', value: string): void
}>()

const fullLabel = computed(() => keyPillLabel(props.condition))
const keyEmpty = computed(() => props.condition.key === '')

const keyDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('keyDropdownRef')
const pillRef = useTemplateRef<InstanceType<typeof InlineEditPill>>('pillRef')

const showValidationErrors = ref(false)

// Entering edit opens the key dropdown, the field the user is here to set.
watch(
  () => props.editing,
  (now) => {
    if (now) {
      void nextTick(() => keyDropdownRef.value?.open())
    } else {
      showValidationErrors.value = false
    }
  },
  { immediate: true }
)

// Emit only the key; the parent infers the level in one mutation (two emits would race and drop it).
function onKeyUpdate(value: string | null): void {
  emit('update:key', value ?? '')
}

const levelInput = computed<string | null>({
  get: () => props.condition.level,
  set: (value) => {
    if (value !== null) {
      emit('update:level', value as GroupLevel)
    }
  }
})

const levelOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: GROUP_LEVELS.map((level) => ({ name: level, title: levelLabel(level) }))
}))

// Veto committing while the key is empty: reveal the error and keep editing.
function canLeave(): boolean {
  if (!isKeyValid(props.condition)) {
    showValidationErrors.value = true
    return false
  }
  return true
}

defineExpose({
  revealValidationErrors: () => {
    showValidationErrors.value = true
  },
  focus: () => {
    pillRef.value?.focus()
  }
})
</script>

<template>
  <InlineEditPill
    ref="pillRef"
    :editing="editing"
    :removable="removable"
    :aria-label="ariaLabel ?? fullLabel"
    :title="fullLabel"
    :edit-aria-label="`${_t('Edit group key')}: ${fullLabel}`"
    :remove-label="_t('Remove group key')"
    :can-leave="canLeave"
    scope-marker-attr="data-gb-scope"
    item-marker-attr="data-gb-item"
    @edit="emit('edit')"
    @remove="emit('remove')"
    @done="emit('done')"
  >
    <template #edit>
      <span
        data-gb-item
        class="metric-backend-group-by-key-pill__segment metric-backend-group-by-key-pill__segment--level"
      >
        <CmkDropdown
          v-model="levelInput"
          :options="levelOptions"
          :label="_t('Attribute level')"
          :input-hint="_t('Attribute level')"
        />
      </span>
      <span
        data-gb-item
        class="metric-backend-group-by-key-pill__segment metric-backend-group-by-key-pill__segment--key"
      >
        <CmkDropdown
          ref="keyDropdownRef"
          :model-value="condition.key || null"
          :options="{ type: 'callback-filtered', querySuggestions }"
          :label="_t('Attribute key')"
          :input-hint="_t('Attribute key')"
          :required="showValidationErrors"
          :form-validation="showValidationErrors && keyEmpty"
          @update:model-value="onKeyUpdate"
        />
      </span>
    </template>
    <template #read-only>
      <span
        class="metric-backend-group-by-key-pill__segment metric-backend-group-by-key-pill__segment--level metric-backend-group-by-key-pill__segment--dimmed"
        >[{{ levelLabel(condition.level) }}]</span
      >
      <span
        class="metric-backend-group-by-key-pill__segment metric-backend-group-by-key-pill__segment--key"
        >{{ condition.key }}</span
      >
    </template>
  </InlineEditPill>
</template>

<style scoped>
.metric-backend-group-by-key-pill__segment {
  padding: var(--dimension-2) var(--dimension-3);
  display: inline-flex;
  align-items: center;
}

.metric-backend-group-by-key-pill__segment--dimmed {
  color: var(--font-color-dimmed);
  font-style: italic;
}
</style>
