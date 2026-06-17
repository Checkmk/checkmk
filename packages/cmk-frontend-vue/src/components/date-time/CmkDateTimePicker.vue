<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="Nullable extends boolean = false">
import { type CalendarDate, type ZonedDateTime } from '@internationalized/date'
import { computed, nextTick, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import {
  MIDNIGHT,
  instantToParts,
  isDateTimeParts,
  isEmptyDateTimePartsDraft,
  partsToInstant
} from './dateTimeUtils'
import DateCalendar from './private/calendar/DateCalendar.vue'
import StackLayout from './private/display/StackLayout.vue'
import VerticalRule from './private/display/VerticalRule.vue'
import DateTimeFlyout from './private/flyout/DateTimeFlyout.vue'
import DateTimeInput from './private/input/DateTimeInput.vue'
import TimeSelector from './private/time-selector/TimeSelector.vue'
import type {
  CmkDateTimePickerProps,
  DateTimePartsDraft,
  DateTimeSaveSlots,
  TimeValue
} from './types'
import { useDateTimeDraft } from './useDateTimeDraft'
import { useResolvedDateTimeSettings } from './useResolvedDateTimeSettings'

type ModelValue = Nullable extends false ? ZonedDateTime : ZonedDateTime | null

const props = withDefaults(defineProps<CmkDateTimePickerProps<Nullable>>(), {
  saveMode: false,
  disabled: false
})

/** The selected instant. `null` is only allowed when `nullable` is set. */
const model = defineModel<ModelValue>({ required: true })
/** Whether the picker flyout is open. */
const open = defineModel<boolean>('open', { default: false })

defineSlots<DateTimeSaveSlots>()

const { _t } = usei18n()

const nullable = props.nullable === true

const settings = useResolvedDateTimeSettings(
  () => props.settings,
  () => props.timeZone
)
/** Whether the footer's Save checkbox is ticked; owned here so the apply orchestration can read it. */
const saveChecked = ref(false)

/** Apply accepts a complete date + time, or an empty draft when the picker is nullable. */
function canApply(value: DateTimePartsDraft) {
  return isDateTimeParts(value) || (nullable && isEmptyDateTimePartsDraft(value))
}

const { draft, pendingSave, confirm, onTriggerFocusOut } = useDateTimeDraft<DateTimePartsDraft>({
  open,
  source: () => instantToParts(model.value, settings.timeZone),
  clone: (value) => ({ date: value.date, time: value.time ? { ...value.time } : null }),
  commit: (value) => {
    // `canApply` has already gated this draft: it is either complete, or empty while nullable.
    if (isDateTimeParts(value)) {
      model.value = partsToInstant(value, settings.timeZone, model.value ?? null) as ModelValue
    } else if (model.value !== null) {
      // Empty draft: clear the (nullable) model, skipping a no-op write.
      model.value = null as ModelValue
    }
    return true
  },
  canApply,
  save: {
    mode: () => props.saveMode,
    checked: saveChecked,
    handler: () => props.saveHandler
  }
})

// Date-only view for the calendar (the input binds the whole `draft`).
const draftDate = computed<CalendarDate | null>({
  get: () => draft.value.date,
  set: (value) => {
    draft.value = { ...draft.value, date: value }
  }
})
const selectorTime = computed<TimeValue>({
  get: () => draft.value.time ?? MIDNIGHT,
  set: (value) => {
    draft.value = { ...draft.value, time: value }
  }
})

const calendar = useTemplateRef<{ focus: () => void }>('calendar')
const triggerInput = useTemplateRef<InstanceType<typeof DateTimeInput>>('triggerInput')

// Clicking into the field opens the popup but leaves focus in the field for
// inline typing; the icon button toggles and, on opening, moves focus into the calendar (APG).
function openFromField(): void {
  open.value = true
}
async function toggleFromButton(): Promise<void> {
  if (open.value) {
    open.value = false
    return
  }
  open.value = true
  await nextTick()
  calendar.value?.focus()
}
</script>

<template>
  <DateTimeFlyout
    v-model:open="open"
    v-model:save-checked="saveChecked"
    :show-actions="true"
    :save-mode="props.saveMode"
    :pending-save="pendingSave"
    :save-label="props.saveLabel ?? _t('Save date & time')"
    :apply-disabled="!canApply(draft)"
    :label="props.label ?? _t('Choose date & time')"
    :restore-focus="() => triggerInput?.focusTriggerButton()"
    @apply="confirm"
  >
    <template #trigger="{ aria }">
      <DateTimeInput
        ref="triggerInput"
        v-model="draft"
        :date-format="settings.dateFormat"
        :month-names="settings.monthNamesLong"
        :hour-cycle="settings.hourCycle"
        :disabled="props.disabled"
        :open="open"
        as-trigger
        :trigger-aria="aria"
        @commit="confirm"
        @open="openFromField"
        @toggle="toggleFromButton"
        @focusout="onTriggerFocusOut"
      />
    </template>

    <StackLayout direction="row">
      <DateCalendar
        ref="calendar"
        v-model:selection="draftDate"
        mode="single"
        :settings="settings"
      />
      <VerticalRule />
      <TimeSelector v-model="selectorTime" :hour-cycle="settings.hourCycle" @commit="confirm" />
    </StackLayout>

    <template #save>
      <slot name="save" />
    </template>
  </DateTimeFlyout>
</template>
