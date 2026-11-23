<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="Nullable extends boolean = false">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import type { TriggerAria } from 'cmk-ui-library/components/CmkFlyout'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkVisuallyHidden from 'cmk-ui-library/components/CmkVisuallyHidden.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import {
  type ComponentPublicInstance,
  computed,
  nextTick,
  reactive,
  ref,
  useTemplateRef
} from 'vue'

import {
  formatTime,
  instantToParts,
  isDateTimeParts,
  isEmptyDateTimePartsDraft,
  isRangeInverted,
  partsToInstant,
  swapRangeEndpoints
} from './dateTimeUtils'
import { focusLeftElement } from './focusLeftElement'
import DateCalendar from './private/calendar/DateCalendar.vue'
import type { CalendarSelection } from './private/calendar/types'
import CmkTimeRangeDisplay from './private/display/CmkTimeRangeDisplay.vue'
import HorizontalRule from './private/display/HorizontalRule.vue'
import TimeZoneInfo from './private/display/TimeZoneInfo.vue'
import DateTimeFlyout from './private/flyout/DateTimeFlyout.vue'
import DateTimeInputRow from './private/input/DateTimeInputRow.vue'
import { presetDraft } from './rangePresets'
import type {
  CmkTimeRangePickerProps,
  DateTimeParts,
  DateTimeRange,
  DateTimeSaveSlots,
  RangeDraft,
  RangePreset,
  ResolvedDateTimeSettings
} from './types'
import { useDateTimeDraft } from './useDateTimeDraft'
import { useResolvedDateTimeSettings } from './useResolvedDateTimeSettings'

type RangeModel = Nullable extends false ? DateTimeRange : DateTimeRange | null

const props = withDefaults(defineProps<CmkTimeRangePickerProps<Nullable>>(), {
  saveMode: false,
  disabled: false
})

/** The selected range. `null` (an empty range) is only allowed when `nullable` is set; a half-empty
 *  range (one endpoint set, the other not) is never representable. */
const model = defineModel<RangeModel>({ required: true })
/** Whether the picker flyout is open. */
const open = defineModel<boolean>('open', { default: false })

defineSlots<
  DateTimeSaveSlots & {
    /**
     * Replaces the default {@link CmkTimeRangeDisplay} trigger.
     * This is a display-only slot: bind `aria` to a focusable element (like a button), and bind
     * `triggerRef` (`:ref="triggerRef"`) onto that same element so focus returns to it when the
     * flyout closes. Endpoints are edited inside the flyout, not the trigger.
     */
    trigger?: (props: {
      open: boolean
      aria: TriggerAria
      triggerRef: (el: Element | ComponentPublicInstance | null) => void
      fields: Readonly<RangeDraft>
      disabled: boolean
      settings: ResolvedDateTimeSettings
    }) => unknown
  }
>()

const { _t } = usei18n()

const nullable = props.nullable === true

const settings = useResolvedDateTimeSettings(
  () => props.settings,
  () => props.timeZone
)
/** Whether the footer's Save checkbox is ticked; owned here so the apply orchestration can read it. */
const saveChecked = ref(false)

/** A range can be applied when both endpoints are complete, or both empty while nullable. */
function canApply(value: RangeDraft) {
  const bothSet = isDateTimeParts(value.from) && isDateTimeParts(value.to)
  const bothEmpty = isEmptyDateTimePartsDraft(value.from) && isEmptyDateTimePartsDraft(value.to)
  return bothSet || (nullable && bothEmpty)
}

const {
  draft,
  pendingSave,
  confirm: confirmDraft
} = useDateTimeDraft<RangeDraft>({
  open,
  source: () => ({
    from: instantToParts(model.value?.from ?? null, settings.timeZone),
    to: instantToParts(model.value?.to ?? null, settings.timeZone)
  }),
  clone: (value) => ({
    from: { date: value.from.date, time: value.from.time ? { ...value.from.time } : null },
    to: { date: value.to.date, time: value.to.time ? { ...value.to.time } : null }
  }),
  canApply,
  save: {
    mode: () => props.saveMode,
    checked: saveChecked,
    handler: () => props.saveHandler
  },
  commit: (value) => {
    // `canApply` has already gated this draft: both endpoints complete, or both empty while nullable.
    if (!isDateTimeParts(value.from) || !isDateTimeParts(value.to)) {
      // Both empty: clear the (nullable) model, skipping a no-op write.
      if (model.value !== null) {
        model.value = null as RangeModel
      }
      return true
    }
    const nextFrom = partsToInstant(value.from, settings.timeZone, model.value?.from ?? null)
    const nextTo = partsToInstant(value.to, settings.timeZone, model.value?.to ?? null)
    // Both set: skip the write when nothing changed, so a no-op Apply never rewrites the model
    // (`partsToInstant` returns the same instant instance when an endpoint wasn't edited).
    if (model.value !== null && nextFrom === model.value.from && nextTo === model.value.to) {
      return true
    }
    model.value = { from: nextFrom, to: nextTo } as RangeModel
    return true
  }
})

function draftField<K extends keyof RangeDraft>(key: K) {
  return computed<RangeDraft[K]>({
    get: () => draft.value[key],
    set: (value) => {
      draft.value = { ...draft.value, [key]: value }
    }
  })
}
/** The staged endpoints as plain writable fields; also handed to the `trigger` slot. */
const fields = reactive({
  from: draftField('from'),
  to: draftField('to')
})

const pendingRange = computed<CalendarSelection>({
  get: () => ({ start: draft.value.from.date, end: draft.value.to.date }),
  set: (selection) => {
    draft.value = {
      from: { ...draft.value.from, date: selection.start },
      to: { ...draft.value.to, date: selection.end }
    }
  }
})

/** Polite live-region text announcing an auto-swap; voiced by a `CmkVisuallyHidden` in the flyout. */
const swapMessage = ref<TranslatedString>(untranslated(''))

/** Spoken "<date> <time>" for one (complete) endpoint, e.g. "June 10, 2026 08:00". */
function describeEndpoint(parts: DateTimeParts): string {
  return `${settings.formatLongDate(parts.date)} ${formatTime(parts.time, settings.hourCycle)}`
}

// Clear before re-announcing: a live region only fires on a *change*, so an identical repeat
// swap message would otherwise stay silent.
async function announceSwap(from: DateTimeParts, to: DateTimeParts): Promise<void> {
  swapMessage.value = untranslated('')
  await nextTick()
  swapMessage.value = _t('Range reordered: start %{start}, end %{end}', {
    start: describeEndpoint(from),
    end: describeEndpoint(to)
  })
}

// Order an inverted range by *swapping* (never shifting), on focus leaving the inputs and on apply.
// Idempotent, so all those call sites can wire it safely.
function swapIfNeeded(): void {
  if (isRangeInverted(draft.value)) {
    const swapped = swapRangeEndpoints(draft.value)
    draft.value = swapped
    // `isRangeInverted` only holds when both endpoints are complete, so the swapped range is too.
    if (isDateTimeParts(swapped.from) && isDateTimeParts(swapped.to)) {
      void announceSwap(swapped.from, swapped.to)
    }
  }
}

// The single apply path for every Enter (From/To rows) and the footer button: order the endpoints
// first (swap mutates `draft` synchronously, so `confirmDraft` then sees the ordered range for its
// `canApply` guard, save handler and commit), then run the shared confirm.
function confirm(): Promise<void> {
  swapIfNeeded()
  return confirmDraft()
}

function applyPreset(preset: RangePreset): Promise<void> {
  if (pendingSave.value) {
    return Promise.resolve()
  }
  draft.value = presetDraft(preset, settings.timeZone)
  return confirm()
}

function onInputAreaFocusOut(event: FocusEvent): void {
  if (focusLeftElement(event)) {
    swapIfNeeded()
  }
}

const calendar = useTemplateRef<{ focus: () => void }>('calendar')

// The trigger's exact focusable control, registered via the `triggerRef` function-ref handed to the
// trigger slot — bound by the default button below, or by a consumer that overrides the slot. Focus
// returns here when the flyout closes with focus inside the popup.
const triggerEl = ref<HTMLElement | null>(null)
function setTriggerRef(el: Element | ComponentPublicInstance | null): void {
  triggerEl.value = el instanceof HTMLElement ? el : null
}
function restoreTriggerFocus(): void {
  triggerEl.value?.focus()
}

// The summary trigger toggles the flyout (CmkFlyout is fully controlled and never toggles itself).
// On opening, focus moves into the calendar so a keyboard user lands on the range straight away.
async function toggleTrigger(): Promise<void> {
  if (props.disabled) {
    return
  }
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
    popup-border="container"
    :save-mode="saveMode"
    :pending-save="pendingSave"
    :save-label="saveLabel ?? _t('Save range')"
    :apply-disabled="!canApply(draft)"
    :apply-disabled-reason="_t('Enter a complete start and end')"
    :label="label ?? _t('Choose a date & time range')"
    :restore-focus="restoreTriggerFocus"
    @apply="confirm"
  >
    <template #trigger="{ aria }">
      <div
        class="cmk-time-range-picker__trigger"
        :class="{
          'cmk-time-range-picker__trigger--open': open,
          'cmk-time-range-picker__trigger--disabled': disabled
        }"
        @click="toggleTrigger"
      >
        <slot
          name="trigger"
          :open="open"
          :aria="aria"
          :trigger-ref="setTriggerRef"
          :fields="fields"
          :disabled="props.disabled"
          :settings="settings"
        >
          <button
            :ref="setTriggerRef"
            type="button"
            class="cmk-time-range-picker__trigger-button"
            v-bind="aria"
            :disabled="props.disabled"
          >
            <CmkTimeRangeDisplay :from="fields.from" :to="fields.to" :settings="settings" />
            <CmkMultitoneIcon
              name="user-interface"
              primary-color="font"
              size="medium"
              aria-hidden="true"
            />
          </button>
        </slot>
      </div>
      <CmkVisuallyHidden :text="swapMessage" live="polite" />
    </template>

    <div class="cmk-time-range-picker__body">
      <div class="cmk-time-range-picker__start">
        <div
          class="cmk-time-range-picker__inputs"
          role="group"
          :aria-label="_t('Time range')"
          @focusout="onInputAreaFocusOut"
        >
          <DateTimeInputRow
            v-model="fields.from"
            :label="_t('From')"
            :date-format="settings.dateFormat"
            :month-names="settings.monthNamesLong"
            :hour-cycle="settings.hourCycle"
            :date-aria-label="_t('From date')"
            :time-aria-label="_t('From time')"
            :time-selector-label="_t('Choose start time')"
            @commit="confirm"
          />
          <DateTimeInputRow
            v-model="fields.to"
            :label="_t('To')"
            :date-format="settings.dateFormat"
            :month-names="settings.monthNamesLong"
            :hour-cycle="settings.hourCycle"
            :date-aria-label="_t('To date')"
            :time-aria-label="_t('To time')"
            :time-selector-label="_t('Choose end time')"
            @commit="confirm"
          />
        </div>
        <div
          v-if="presets && presets.length"
          class="cmk-time-range-picker__presets"
          role="group"
          :aria-label="_t('Quick range presets')"
        >
          <CmkButton
            v-for="preset in presets"
            :key="preset.id"
            size="small"
            :disabled="pendingSave"
            @click="applyPreset(preset)"
          >
            {{ preset.label }}
          </CmkButton>
        </div>
      </div>

      <DateCalendar
        ref="calendar"
        v-model:selection="pendingRange"
        class="cmk-time-range-picker__calendar"
        mode="range"
        :settings="settings"
      />

      <HorizontalRule class="cmk-time-range-picker__rule" />

      <TimeZoneInfo
        class="cmk-time-range-picker__zones"
        :settings="settings"
        :server-time-zone="serverTimeZone"
      />
    </div>

    <template #save>
      <slot name="save" />
    </template>
  </DateTimeFlyout>
</template>

<style scoped>
.cmk-time-range-picker__trigger {
  border: 1px solid transparent;
  border-radius: var(--dimension-3);
  cursor: pointer;
}

.cmk-time-range-picker__trigger:not(
    .cmk-time-range-picker__trigger--open,
    .cmk-time-range-picker__trigger--disabled
  ):hover {
  background: var(--background-hover-wash);
}

.cmk-time-range-picker__trigger--open {
  background: var(--default-bg-color);
  border-color: var(--cmk-flyout-popup-border-color, var(--default-form-element-border-color));
  border-bottom-color: transparent;
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.cmk-time-range-picker__trigger--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Chrome-less button so the trigger looks unchanged at rest; it only adds keyboard focusability
   (Enter/Space → click bubbles to the trigger area's `toggleTrigger`) and a focus ring. */
.cmk-time-range-picker__trigger-button {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5) var(--dimension-3);
  border: none;
  border-radius: var(--dimension-3);
  background: none;
  font: inherit;
  color: inherit;
  text-align: inherit;
  cursor: inherit;
}

.cmk-time-range-picker__trigger-button:focus-visible {
  outline: revert;
}

.cmk-time-range-picker__body {
  display: grid;
  grid-template-columns: repeat(3, max-content);
  align-items: start;
  column-gap: var(--dimension-4);
  padding: var(--dimension-7) var(--dimension-7) 0 var(--dimension-5);
}

.cmk-time-range-picker__start {
  display: grid;
  grid-column: 1 / 3;
  grid-template-columns: subgrid;
  row-gap: var(--dimension-8);
}

.cmk-time-range-picker__inputs {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  row-gap: var(--dimension-4);
}

.cmk-time-range-picker__presets {
  display: flex;
  grid-column: 2;
  flex-direction: column;
  align-items: start;
  gap: var(--dimension-4);
}

.cmk-time-range-picker__calendar {
  margin-left: calc(var(--dimension-10) - var(--dimension-4));
}

.cmk-time-range-picker__body > .cmk-time-range-picker__rule {
  grid-column: 1 / -1;
  width: auto;
  margin: var(--dimension-7) calc(-1 * var(--dimension-7)) 0 calc(-1 * var(--dimension-5));
}

.cmk-time-range-picker__zones {
  grid-column: 2 / -1;
  padding: var(--dimension-5) 0;
}
</style>
