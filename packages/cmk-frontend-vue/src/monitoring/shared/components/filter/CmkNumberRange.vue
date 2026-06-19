<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

export interface NumberRange {
  from: number | undefined
  to: number | undefined
}

const {
  fromLabel,
  toLabel,
  unit = ''
} = defineProps<{
  /** Visible/aria label for the lower bound. Defaults to a translated "From". */
  fromLabel?: string
  /** Visible/aria label for the upper bound. Defaults to a translated "To". */
  toLabel?: string
  /** Unit suffix shown after the upper-bound field (e.g. "ms", "services"). */
  unit?: string
}>()

const model = defineModel<NumberRange>({ default: () => ({ from: undefined, to: undefined }) })

const emit = defineEmits<{ 'update:valid': [valid: boolean] }>()

const { _t } = usei18n()

const fromText = computed(() => fromLabel ?? _t('From'))
const toText = computed(() => toLabel ?? _t('To'))

function normalize(value: number | undefined): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

const from = computed<number | undefined>({
  get: () => model.value.from,
  set: (value) => {
    model.value = { ...model.value, from: normalize(value) }
  }
})

const to = computed<number | undefined>({
  get: () => model.value.to,
  set: (value) => {
    model.value = { ...model.value, to: normalize(value) }
  }
})

const rangeErrors = computed<string[]>(() => {
  const { from: f, to: t } = model.value
  if (f !== undefined && t !== undefined) {
    if (isNaN(f) || isNaN(t)) {
      return [_t('Only number values are allowed.')]
    }
    if (f > t) {
      return [_t('The lower bound must not exceed the upper bound.')]
    }
  }

  return []
})

watch(rangeErrors, (errors) => emit('update:valid', errors.length === 0), { immediate: true })
</script>

<template>
  <div class="monitoring-cmk-number-range">
    <div class="monitoring-cmk-number-range__fields">
      <label class="monitoring-cmk-number-range__field">
        <span class="monitoring-cmk-number-range__label">{{ fromText }}</span>
        <CmkInput v-model="from" type="number" :aria-label="fromText" />
      </label>
      <label class="monitoring-cmk-number-range__field">
        <span class="monitoring-cmk-number-range__label">{{ toText }}</span>
        <CmkInput v-model="to" type="number" :unit="unit" :aria-label="toText" />
      </label>
    </div>
    <CmkInlineValidation :validation="rangeErrors" />
  </div>
</template>

<style scoped>
.monitoring-cmk-number-range {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.monitoring-cmk-number-range__fields {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.monitoring-cmk-number-range__field {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
}

.monitoring-cmk-number-range__label {
  color: var(--font-color-dimmed);
}
</style>
