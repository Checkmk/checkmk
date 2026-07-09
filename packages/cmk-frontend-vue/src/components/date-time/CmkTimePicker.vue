<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="Nullable extends boolean = false">
import { computed, nextTick, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import { MIDNIGHT } from './dateTimeUtils'
import DateTimeFlyout from './private/flyout/DateTimeFlyout.vue'
import TimeInput from './private/input/TimeInput.vue'
import TimeSelector from './private/time-selector/TimeSelector.vue'
import type { CmkTimePickerProps, TimeValue } from './types'
import { useDateTimeDraft } from './useDateTimeDraft'
import { useResolvedDateTimeSettings } from './useResolvedDateTimeSettings'

type ModelValue = Nullable extends false ? TimeValue : TimeValue | null

const props = withDefaults(defineProps<CmkTimePickerProps<Nullable>>(), {
  disabled: false
})

/** The selected wall-clock time. `null` is only allowed when `nullable` is set. */
const model = defineModel<ModelValue>({ required: true })
/** Whether the picker flyout is open. */
const open = defineModel<boolean>('open', { default: false })

const { _t } = usei18n()

const nullable = props.nullable === true

// No timezone here: a clock time is wall-clock only; nothing in this picker deals in instants.
const settings = useResolvedDateTimeSettings(() => props.settings)

/** A picked time can be applied; an empty one only when the picker is nullable. */
function canApply(value: TimeValue | null) {
  return nullable || value !== null
}

const { draft, confirm, onTriggerFocusOut } = useDateTimeDraft<TimeValue | null>({
  open,
  source: () => model.value,
  clone: (value) => (value ? { ...value } : null),
  commit: (value) => {
    if (value === null && !nullable) {
      return false
    }
    model.value = value as ModelValue
    return true
  },
  canApply
})

// The wheel selector always shows a concrete time; an untouched (null) draft is only materialized
// once the user actually picks, so an empty time stays empty until then.
const selectorTime = computed<TimeValue>({
  get: () => draft.value ?? MIDNIGHT,
  set: (value) => {
    draft.value = value
  }
})

const selector = useTemplateRef<{ focus: () => void }>('selector')
const triggerInput = useTemplateRef<InstanceType<typeof TimeInput>>('triggerInput')

// Clicking into the field opens the popup but leaves focus in the field for
// inline typing; the icon button toggles and, on opening, moves focus into the wheel (APG).
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
  selector.value?.focus()
}
</script>

<template>
  <DateTimeFlyout
    v-model:open="open"
    class="cmk-time-picker__flyout"
    popup-background="solid"
    :show-actions="true"
    stretch-actions
    :apply-disabled="!canApply(draft)"
    :label="label ?? _t('Choose a time')"
    :restore-focus="() => triggerInput?.focusTriggerButton()"
    @apply="confirm"
  >
    <template #trigger="{ open: isOpen, aria }">
      <TimeInput
        ref="triggerInput"
        v-model="draft"
        :hour-cycle="settings.hourCycle"
        :disabled="disabled"
        :open="isOpen"
        :trigger-aria="aria"
        @commit="confirm"
        @open="openFromField"
        @toggle="toggleFromButton"
        @focusout="onTriggerFocusOut"
      />
    </template>

    <TimeSelector
      ref="selector"
      v-model="selectorTime"
      class="cmk-time-picker__selector"
      :hour-cycle="settings.hourCycle"
      @commit="confirm"
    />
  </DateTimeFlyout>
</template>

<style scoped>
.cmk-time-picker__flyout {
  --cmk-dt-flyout-footer-padding: var(--dimension-3);
}

.cmk-time-picker__selector {
  padding: var(--dimension-3);
}
</style>
