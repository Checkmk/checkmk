<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="F extends FilterField">
import { type ZonedDateTime, fromDate, getLocalTimeZone } from '@internationalized/date'
import CmkDateTimePicker from 'cmk-ui-library/components/date-time/CmkDateTimePicker.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { shallowRef, watch } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

import type { DateTimeRangeFilter } from './types'

const props = defineProps<{ definition: DateTimeRangeFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })

const emit = defineEmits<{ 'update:valid': [valid: boolean] }>()

const { _t } = usei18n()

const timeZone = getLocalTimeZone()

function toInstant(unixSeconds: number): ZonedDateTime {
  return fromDate(new Date(unixSeconds * 1000), timeZone)
}

function toUnixSeconds(instant: ZonedDateTime): number {
  return Math.floor(instant.toDate().getTime() / 1000)
}

function boundFrom(node: ColumnFilterNode<F> | undefined, op: 'gte' | 'lte'): ZonedDateTime | null {
  if (!node) {
    return null
  }
  const conditions = node.type === 'and' ? node.children : [node]
  for (const condition of conditions) {
    if (condition.type === 'condition' && 'op' in condition && condition.op === op) {
      return toInstant(condition.value as number)
    }
  }
  return null
}

const from = shallowRef<ZonedDateTime | null>(boundFrom(model.value, 'gte'))
const to = shallowRef<ZonedDateTime | null>(boundFrom(model.value, 'lte'))

function condition(op: 'gte' | 'lte', instant: ZonedDateTime): ColumnFilterNode<F> {
  return {
    type: 'condition',
    field: props.definition.field,
    op,
    value: toUnixSeconds(instant)
  } as ColumnFilterNode<F>
}

function isOrdered(): boolean {
  return from.value === null || to.value === null || from.value.compare(to.value) <= 0
}

watch(
  [from, to],
  () => {
    emit('update:valid', isOrdered())
    if (!isOrdered()) {
      return
    }
    const conditions: ColumnFilterNode<F>[] = []
    if (from.value !== null) {
      conditions.push(condition('gte', from.value))
    }
    if (to.value !== null) {
      conditions.push(condition('lte', to.value))
    }
    if (conditions.length === 0) {
      model.value = undefined
    } else if (conditions.length === 1) {
      model.value = conditions[0]
    } else {
      model.value = { type: 'and', children: conditions } as ColumnFilterNode<F>
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="monitoring-filter-date-time-range">
    <div class="monitoring-filter-date-time-range__row" role="group" :aria-label="_t('From')">
      <span class="monitoring-filter-date-time-range__label">{{ _t('From') }}</span>
      <CmkDateTimePicker
        v-model="from"
        :nullable="true"
        :label="_t('Choose the earliest date & time')"
      />
    </div>

    <div class="monitoring-filter-date-time-range__row" role="group" :aria-label="_t('To')">
      <span class="monitoring-filter-date-time-range__label">{{ _t('To') }}</span>
      <CmkDateTimePicker
        v-model="to"
        :nullable="true"
        :label="_t('Choose the latest date & time')"
      />
    </div>
  </div>
</template>

<style scoped>
.monitoring-filter-date-time-range {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  padding: var(--dimension-2);
}

.monitoring-filter-date-time-range__row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.monitoring-filter-date-time-range__label {
  min-width: var(--dimension-11);
}
</style>
