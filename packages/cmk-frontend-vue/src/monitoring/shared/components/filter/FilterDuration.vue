<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Content component for the "duration" filter type. It filters a timestamp field
by age rather than by instant: a toggle picks whether the age has to be below
the entered value, above it, or between two of them, and a unit dropdown says
what the numbers count in.

The v-model is a `ColumnFilterNode<F>` (or undefined for "no filter") carrying
`age` bounds, which state the age itself rather than the instant it currently
resolves to - `MonitoringApi` resolves them as it builds each request, so the
filter keeps meaning what it says while the table polls.

What the user typed outlives every switch. The first number is the same field in
all three modes, so switching only adds or drops the second bound, and changing
the unit reads the same numbers in the new unit rather than converting them, so
"5" stays "5" when minutes become hours. The unit an existing filter reopens in
is the coarsest one all its bounds divide evenly by, so the numbers read back
exactly as they were typed.

The parent `FilterDropdown` owns the popover shell and Clear/Apply handling, and
calls `validate` before it commits, which is when a negative age or an inverted
span reports itself.
-->
<script setup lang="ts" generic="F extends FilterField">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import CmkToggleButtonGroup, {
  type ToggleButtonOption
} from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref, watch } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

import type { DurationFilter } from './types'

type AgeOp = 'younger_than' | 'older_than'

const props = defineProps<{ definition: DurationFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })

const { _t } = usei18n()

const YOUNGER_OPTION = 'younger'
const OLDER_OPTION = 'older'
const BETWEEN_OPTION = 'between'

const UNIT_SECONDS: Record<string, number> = {
  seconds: 1,
  minutes: 60,
  hours: 3600,
  days: 86400
}

const UNITS_COARSEST_FIRST = ['days', 'hours', 'minutes', 'seconds']

const DEFAULT_UNIT = 'minutes'

function agesOf(node: ColumnFilterNode<F> | undefined): Partial<Record<AgeOp, number>> {
  const ages: Partial<Record<AgeOp, number>> = {}
  if (!node) {
    return ages
  }
  for (const bound of node.type === 'and' ? node.children : [node]) {
    if (bound.type === 'age') {
      ages[bound.op] = bound.seconds
    }
  }
  return ages
}

// The coarsest unit every entered age divides evenly by, so reopening a filter
// reads its numbers back as they were typed rather than rounded.
function unitOf(ages: (number | undefined)[]): string {
  const entered = ages.filter((age): age is number => age !== undefined && age > 0)
  if (entered.length === 0) {
    return DEFAULT_UNIT
  }
  return (
    UNITS_COARSEST_FIRST.find((unit) => entered.every((age) => age % UNIT_SECONDS[unit]! === 0)) ??
    DEFAULT_UNIT
  )
}

const initialAges = agesOf(model.value)

function initialSelection(): string {
  if (initialAges.older_than !== undefined && initialAges.younger_than !== undefined) {
    return BETWEEN_OPTION
  }
  return initialAges.older_than !== undefined ? OLDER_OPTION : YOUNGER_OPTION
}

const selected = ref<string>(initialSelection())
const unit = ref<string>(unitOf([initialAges.older_than, initialAges.younger_than]))

function inUnit(seconds: number | undefined): number | undefined {
  return seconds === undefined ? undefined : seconds / UNIT_SECONDS[unit.value]!
}

// The number the sentence leads with, whichever mode is picked: the whole age for
// "More than" and "Less than", the younger end of the span for "Between".
const first = ref<number | undefined>(inUnit(initialAges.older_than ?? initialAges.younger_than))

// The older end of a span, so only "Between" shows it.
const second = ref<number | undefined>(
  initialAges.older_than === undefined ? undefined : inUnit(initialAges.younger_than)
)

const options = computed<ToggleButtonOption[]>(() => [
  { label: _t('More than'), value: OLDER_OPTION },
  { label: _t('Less than'), value: YOUNGER_OPTION },
  { label: _t('Between'), value: BETWEEN_OPTION }
])

// The picked toggle leads the input row, so the row reads as a sentence:
// "Less than [5] minutes ago", "Between [5] and [30] minutes ago".
const selectedLabel = computed<string>(
  () => options.value.find((option) => option.value === selected.value)?.label ?? ''
)

const unitOptions = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: [
    { name: 'seconds', title: _t('seconds') },
    { name: 'minutes', title: _t('minutes') },
    { name: 'hours', title: _t('hours') },
    { name: 'days', title: _t('days') }
  ]
}))

const errors = ref<string[]>([])

const validationId = useId()

function ageBound(op: AgeOp, value: number): ColumnFilterNode<F> {
  return {
    type: 'age',
    field: props.definition.field,
    op,
    seconds: value * UNIT_SECONDS[unit.value]!
  } as ColumnFilterNode<F>
}

function createFilterNode(): void {
  const bounds: ColumnFilterNode<F>[] = []

  if (selected.value === BETWEEN_OPTION) {
    if (first.value !== undefined) {
      bounds.push(ageBound('older_than', first.value))
    }
    if (second.value !== undefined) {
      bounds.push(ageBound('younger_than', second.value))
    }
  } else if (first.value !== undefined) {
    bounds.push(
      ageBound(selected.value === OLDER_OPTION ? 'older_than' : 'younger_than', first.value)
    )
  }

  if (bounds.length === 0) {
    model.value = undefined
  } else if (bounds.length === 1) {
    model.value = bounds[0]
  } else {
    model.value = { type: 'and', children: bounds } as ColumnFilterNode<F>
  }
}

watch([selected, unit, first, second], () => {
  errors.value = []
  createFilterNode()
})

// An age is only judged when the user commits, so typing the second bound after
// the first one is not flagged mid-keystroke.
function validate(): boolean {
  const entered = selected.value === BETWEEN_OPTION ? [first.value, second.value] : [first.value]
  if (entered.some((age) => age !== undefined && age < 0)) {
    errors.value = [_t('Enter an age of zero or more.')]
  } else if (
    selected.value === BETWEEN_OPTION &&
    first.value !== undefined &&
    second.value !== undefined &&
    first.value > second.value
  ) {
    errors.value = [_t('Enter a younger bound that does not exceed the older one.')]
  } else {
    errors.value = []
  }
  return errors.value.length === 0
}

defineExpose({ validate })
</script>

<template>
  <div class="monitoring-filter-duration">
    <div class="monitoring-filter-duration__options" role="group" :aria-label="_t('Age')">
      <CmkToggleButtonGroup v-model="selected" :options="options" size="small" spacing="none" />
    </div>

    <div class="monitoring-filter-duration__fields">
      <span>{{ selectedLabel }}</span>
      <CmkInput
        v-model="first"
        type="number"
        :aria-label="selected === BETWEEN_OPTION ? _t('Younger bound') : _t('Age')"
        :external-errors="errors"
        :described-by="validationId"
        hide-validation-message
      />
      <template v-if="selected === BETWEEN_OPTION">
        <span>{{ _t('and') }}</span>
        <CmkInput
          v-model="second"
          type="number"
          :aria-label="_t('Older bound')"
          :external-errors="errors"
          :described-by="validationId"
          hide-validation-message
        />
      </template>
      <CmkDropdown v-model="unit" :options="unitOptions" :label="_t('Unit')" />
      <span>{{ _t('ago') }}</span>
    </div>
    <CmkInlineValidation :id="validationId" :validation="errors" />
  </div>
</template>

<style scoped>
.monitoring-filter-duration {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  padding: var(--dimension-3) var(--dimension-5);
}

.monitoring-filter-duration__options {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  padding: 0 var(--dimension-2);
}

.monitoring-filter-duration__fields {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: 0 var(--dimension-2);
}
</style>
