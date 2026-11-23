<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, nextTick, ref, useTemplateRef } from 'vue'

import { MIDNIGHT } from '../../dateTimeUtils'
import type { DateFormatParts, DateTimePartsDraft, HourCycle, TimeValue } from '../../types'
import { useDateTimeDraft } from '../../useDateTimeDraft'
import DateTimeFlyout from '../flyout/DateTimeFlyout.vue'
import TimeSelector from '../time-selector/TimeSelector.vue'
import DateTimeInput from './DateTimeInput.vue'

const props = defineProps<{
  /** Leading row label (e.g. "From" / "To"). */
  label: TranslatedString
  /** Resolved date section order/separator (e.g. `settings.dateFormat` from the resolver). */
  dateFormat: DateFormatParts
  /** Full month names (index 0 = January) for the month segment's spoken value. */
  monthNames: TranslatedString[]
  /** Resolved 12h/24h display cycle (e.g. `settings.hourCycle` from the resolver). */
  hourCycle: HourCycle
  /** Render the field non-interactive and dimmed. */
  disabled?: boolean
  /** Accessible name for the date field; defaults to "Date". */
  dateAriaLabel?: TranslatedString | undefined
  /** Accessible name for the time field; defaults to "Time". */
  timeAriaLabel?: TranslatedString | undefined
  /** Accessible name for the clock button that opens the time selector. */
  timeSelectorLabel: TranslatedString
}>()

/** The endpoint's staged wall-clock draft. Forwarded as-is to the inner {@link DateTimeInput}. */
const model = defineModel<DateTimePartsDraft>({ required: true })

const emit = defineEmits<{
  /** The user requested commit (Enter in a segment). */
  (e: 'commit'): void
}>()

const { _t } = usei18n()

const timeOpen = ref(false)

const { draft: timeDraft, confirm: confirmTime } = useDateTimeDraft<TimeValue | null>({
  open: timeOpen,
  source: () => model.value.time,
  clone: (value) => (value ? { ...value } : null),
  canApply: (value) => value !== null,
  commit: (time) => {
    model.value = { ...model.value, time }
    return true
  }
})

const selectorTime = computed<TimeValue>({
  get: () => timeDraft.value ?? MIDNIGHT,
  set: (value) => {
    timeDraft.value = value
  }
})

const selector = useTemplateRef<{ focus: () => void }>('selector')
const input = useTemplateRef<InstanceType<typeof DateTimeInput>>('input')

async function toggleTimeSelector(): Promise<void> {
  if (timeOpen.value) {
    timeOpen.value = false
    return
  }
  timeOpen.value = true
  await nextTick()
  selector.value?.focus()
}
</script>

<template>
  <div class="cmk-date-time-input-row">
    <CmkLabel aria-hidden="true">{{ props.label }}</CmkLabel>
    <DateTimeFlyout
      v-model:open="timeOpen"
      class="cmk-date-time-input-row__time-flyout"
      popup-background="solid"
      :show-actions="true"
      stretch-actions
      :apply-disabled="timeDraft === null"
      :label="_t('Choose a time')"
      :restore-focus="() => input?.focusTriggerButton()"
      @apply="confirmTime"
    >
      <template #trigger="{ open: isOpen, aria }">
        <DateTimeInput
          ref="input"
          v-model="model"
          :date-format="props.dateFormat"
          :month-names="props.monthNames"
          :hour-cycle="props.hourCycle"
          icon="waiting"
          icon-position="end"
          :icon-label="props.timeSelectorLabel"
          :disabled="props.disabled"
          :date-aria-label="props.dateAriaLabel"
          :time-aria-label="props.timeAriaLabel"
          :open="isOpen"
          as-trigger
          :trigger-aria="aria"
          @commit="emit('commit')"
          @toggle="toggleTimeSelector"
        />
      </template>

      <TimeSelector
        ref="selector"
        v-model="selectorTime"
        class="cmk-date-time-input-row__selector"
        :hour-cycle="props.hourCycle"
        @commit="confirmTime"
      />
    </DateTimeFlyout>
  </div>
</template>

<style scoped>
/* Spans the owner's label | field grid columns so stacked rows share them. */
.cmk-date-time-input-row {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  align-items: center;
}

.cmk-date-time-input-row > :first-child {
  justify-self: end;
}

.cmk-date-time-input-row__time-flyout {
  --cmk-dt-flyout-footer-padding: var(--dimension-3);
}

.cmk-date-time-input-row__selector {
  padding: var(--dimension-3);
}
</style>
