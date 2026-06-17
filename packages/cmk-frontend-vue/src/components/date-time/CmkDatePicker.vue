<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="Nullable extends boolean = false">
import type { CalendarDate } from '@internationalized/date'
import { nextTick, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import DateCalendar from './private/calendar/DateCalendar.vue'
import StackLayout from './private/display/StackLayout.vue'
import DateTimeFlyout from './private/flyout/DateTimeFlyout.vue'
import DateInput from './private/input/DateInput.vue'
import type { CmkDatePickerProps, DateTimeSaveSlots } from './types'
import { useDateTimeDraft } from './useDateTimeDraft'
import { useResolvedDateTimeSettings } from './useResolvedDateTimeSettings'

type ModelValue = Nullable extends false ? CalendarDate : CalendarDate | null

const props = withDefaults(defineProps<CmkDatePickerProps<Nullable>>(), {
  saveMode: false,
  disabled: false
})

/** The selected date. `null` is only allowed when `nullable` is set. */
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

/** A complete value can be applied; a missing one only when the picker is nullable. */
function canApply(value: CalendarDate | null) {
  return nullable || value !== null
}

const { draft, pendingSave, confirm, onTriggerFocusOut } = useDateTimeDraft<CalendarDate | null>({
  open,
  source: () => model.value,
  clone: (value) => value,
  commit: (value) => {
    if (value === null && !nullable) {
      return false
    }
    model.value = value as ModelValue
    return true
  },
  canApply,
  save: {
    mode: () => props.saveMode,
    checked: saveChecked,
    handler: () => props.saveHandler
  }
})

const calendar = useTemplateRef<{ focus: () => void }>('calendar')
const triggerInput = useTemplateRef<InstanceType<typeof DateInput>>('triggerInput')

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
    :save-mode="saveMode"
    :pending-save="pendingSave"
    :save-label="saveLabel ?? _t('Save date')"
    :apply-disabled="!canApply(draft)"
    :label="label ?? _t('Choose a date')"
    :restore-focus="() => triggerInput?.focusTriggerButton()"
    @apply="confirm"
  >
    <template #trigger="{ aria }">
      <DateInput
        ref="triggerInput"
        v-model="draft"
        :date-format="settings.dateFormat"
        :month-names="settings.monthNamesLong"
        :disabled="disabled"
        :open="open"
        :trigger-aria="aria"
        @commit="confirm"
        @open="openFromField"
        @toggle="toggleFromButton"
        @focusout="onTriggerFocusOut"
      />
    </template>

    <StackLayout>
      <DateCalendar ref="calendar" v-model:selection="draft" mode="single" :settings="settings" />
    </StackLayout>

    <template #save>
      <slot name="save" />
    </template>
  </DateTimeFlyout>
</template>
