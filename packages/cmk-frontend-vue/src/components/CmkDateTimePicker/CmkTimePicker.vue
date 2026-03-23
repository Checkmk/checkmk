<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import { untranslated } from '@/lib/i18n'
import useClickOutside from '@/lib/useClickOutside'

import CmkIconButton from '@/components/CmkIconButton.vue'

const { _t } = usei18n()
const vClickOutside = useClickOutside()

const model = defineModel<string>({ required: true })

function parseTime(val: string): { hours: number; minutes: number } | null {
  const match = val.match(/^(\d{1,2}):(\d{2})$/)
  if (!match) {
    return null
  }
  const h = parseInt(match[1]!)
  const m = parseInt(match[2]!)
  if (h < 0 || h > 23 || m < 0 || m > 59) {
    return null
  }
  return { hours: h, minutes: m }
}

function pad(n: number): string {
  return n.toString().padStart(2, '0')
}

const parsed = parseTime(model.value)
const hours = ref(parsed?.hours ?? 0)
const minutes = ref(parsed?.minutes ?? 0)
const popupOpen = ref(false)

const hoursRef = ref<HTMLInputElement | null>(null)
const minutesRef = ref<HTMLInputElement | null>(null)
const hoursColumnRef = ref<HTMLDivElement | null>(null)
const minutesColumnRef = ref<HTMLDivElement | null>(null)

const hoursDisplay = ref(pad(hours.value))
const minutesDisplay = ref(pad(minutes.value))
let isTypingHours = false
let isTypingMinutes = false

const timeString = computed(() => `${pad(hours.value)}:${pad(minutes.value)}`)
const allHours = Array.from({ length: 24 }, (_, i) => i)
const allMinutes = Array.from({ length: 60 }, (_, i) => i)

watch([hours, minutes], () => {
  model.value = timeString.value
})

watch(
  hours,
  () => {
    if (!isTypingHours) {
      hoursDisplay.value = pad(hours.value)
    }
  },
  { flush: 'sync' }
)

watch(
  minutes,
  () => {
    if (!isTypingMinutes) {
      minutesDisplay.value = pad(minutes.value)
    }
  },
  { flush: 'sync' }
)

watch(model, (newVal) => {
  if (newVal === timeString.value) {
    return
  }
  const p = parseTime(newVal)
  if (p) {
    hours.value = p.hours
    minutes.value = p.minutes
  }
})

function wrap(val: number, min: number, max: number): number {
  if (val > max) {
    return min
  }
  if (val < min) {
    return max
  }
  return val
}

function onHoursKey(e: KeyboardEvent) {
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    hours.value = wrap(hours.value + 1, 0, 23)
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    hours.value = wrap(hours.value - 1, 0, 23)
  } else if (e.key === 'ArrowRight' || e.key === ':') {
    e.preventDefault()
    minutesRef.value?.focus()
    minutesRef.value?.select()
  }
}

function onMinutesKey(e: KeyboardEvent) {
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    minutes.value = wrap(minutes.value + 1, 0, 59)
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    minutes.value = wrap(minutes.value - 1, 0, 59)
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault()
    hoursRef.value?.focus()
    hoursRef.value?.select()
  }
}

function onHoursInput(e: Event) {
  const input = e.target as HTMLInputElement
  const raw = input.value.replace(/\D/g, '').slice(0, 2)

  if (raw.length === 0) {
    return
  }

  isTypingHours = true
  const val = parseInt(raw)
  if (!isNaN(val)) {
    hours.value = Math.min(val, 23)
  }

  if (raw.length >= 2) {
    hoursDisplay.value = pad(hours.value)
    isTypingHours = false
    void nextTick(() => {
      minutesRef.value?.focus()
      minutesRef.value?.select()
    })
  } else {
    hoursDisplay.value = raw
    isTypingHours = false
  }
}

function onMinutesInput(e: Event) {
  const input = e.target as HTMLInputElement
  const raw = input.value.replace(/\D/g, '').slice(0, 2)

  if (raw.length === 0) {
    return
  }

  isTypingMinutes = true
  const val = parseInt(raw)
  if (!isNaN(val)) {
    minutes.value = Math.min(val, 59)
  }

  if (raw.length >= 2) {
    minutesDisplay.value = pad(minutes.value)
  } else {
    minutesDisplay.value = raw
  }
  isTypingMinutes = false
}

function selectOnFocus(e: FocusEvent) {
  ;(e.target as HTMLInputElement).select()
}

function onHoursBlur() {
  hoursDisplay.value = pad(hours.value)
}

function onMinutesBlur() {
  minutesDisplay.value = pad(minutes.value)
}

function togglePopup() {
  popupOpen.value = !popupOpen.value
  if (popupOpen.value) {
    void nextTick(() => {
      scrollToSelected()
    })
  }
}

function selectHour(h: number) {
  hours.value = h
}

function selectMinute(m: number) {
  minutes.value = m
}

function scrollToSelected() {
  const hEl = hoursColumnRef.value?.querySelector('.cmk-time-picker__option--selected')
  const mEl = minutesColumnRef.value?.querySelector('.cmk-time-picker__option--selected')
  hEl?.scrollIntoView({ block: 'center' })
  mEl?.scrollIntoView({ block: 'center' })
}
</script>

<template>
  <span v-click-outside="() => (popupOpen = false)" class="cmk-time-picker">
    <!-- eslint-disable vue/no-bare-strings-in-template -->
    <span class="cmk-time-picker__field">
      <input
        ref="hoursRef"
        class="cmk-time-picker__segment"
        type="text"
        inputmode="numeric"
        :value="hoursDisplay"
        maxlength="2"
        size="2"
        :aria-label="_t('Hours')"
        @input="onHoursInput"
        @keydown="onHoursKey"
        @focus="selectOnFocus"
        @blur="onHoursBlur"
      />
      <span class="cmk-time-picker__separator">:</span>
      <input
        ref="minutesRef"
        class="cmk-time-picker__segment"
        type="text"
        inputmode="numeric"
        :value="minutesDisplay"
        maxlength="2"
        size="2"
        :aria-label="_t('Minutes')"
        @input="onMinutesInput"
        @keydown="onMinutesKey"
        @focus="selectOnFocus"
        @blur="onMinutesBlur"
      />
    </span>
    <CmkIconButton
      class="cmk-time-picker__trigger"
      name="clock"
      size="medium"
      :aria-label="_t('Open time picker')"
      @click="togglePopup"
    />
    <!-- eslint-enable vue/no-bare-strings-in-template -->
    <div v-if="popupOpen" class="cmk-time-picker__popup">
      <div ref="hoursColumnRef" class="cmk-time-picker__column">
        <div class="cmk-time-picker__column-header">{{ untranslated('H') }}</div>
        <button
          v-for="h in allHours"
          :key="h"
          type="button"
          class="cmk-time-picker__option"
          :class="{ 'cmk-time-picker__option--selected': h === hours }"
          @click="selectHour(h)"
        >
          {{ pad(h) }}
        </button>
      </div>
      <div ref="minutesColumnRef" class="cmk-time-picker__column">
        <div class="cmk-time-picker__column-header">{{ untranslated('M') }}</div>
        <button
          v-for="m in allMinutes"
          :key="m"
          type="button"
          class="cmk-time-picker__option"
          :class="{ 'cmk-time-picker__option--selected': m === minutes }"
          @click="selectMinute(m)"
        >
          {{ pad(m) }}
        </button>
      </div>
    </div>
  </span>
</template>

<style scoped>
.cmk-time-picker {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
}

.cmk-time-picker__field {
  display: inline-flex;
  align-items: center;
  gap: 0;
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--dimension-3);
  padding: var(--dimension-1) 6px;
  background: var(--default-form-element-bg-color);
  font-family: monospace;
  font-size: 11px;
  line-height: 17px;
  height: 21px;
  box-sizing: border-box;
  font-variant-numeric: tabular-nums;
}

.cmk-time-picker .cmk-time-picker__segment {
  width: 2ch;
  border: none;
  background: transparent;
  color: var(--font-color);
  font-family: monospace;
  font-size: 11px;
  line-height: 17px;
  text-align: center;
  padding: 0;
  margin: 0;
  border-radius: var(--dimension-2);
  outline: none;
  height: auto;
  box-shadow: none;

  &:focus {
    background: var(--success);
    color: var(--font-color-light-bg);
  }
}

.cmk-time-picker__separator {
  color: var(--font-color-dimmed);
  padding: 0 var(--dimension-1);
}

.cmk-time-picker__trigger {
  opacity: 0.7;

  &:hover {
    opacity: 1;
  }
}

.cmk-time-picker__popup {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: var(--z-index-modal-popup, 3500);
  display: flex;
  gap: var(--dimension-2);
  margin-top: var(--dimension-3);
  background: var(--default-bg-color);
  border: 1px solid var(--default-border-color);
  border-radius: 6px;
  padding: var(--dimension-3);
  box-shadow: 0 4px 12px rgb(0 0 0 / 30%);
}

.cmk-time-picker__column {
  display: flex;
  flex-direction: column;
  max-height: 200px;
  overflow: hidden auto;
  width: 48px;
  scrollbar-width: thin;
  scrollbar-color: var(--scrollbar-color, #888) transparent;
}

.cmk-time-picker__column-header {
  position: sticky;
  top: 0;
  background: var(--default-bg-color);
  color: var(--font-color-dimmed);
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  padding: var(--dimension-3) 0;
  border-bottom: 1px solid var(--default-border-color);
}

.cmk-time-picker__option {
  display: block;
  width: 100%;
  margin: 0;
  border: none;
  border-radius: 3px;
  background: transparent;
  color: var(--font-color);
  font-family: monospace;
  font-size: 13px;
  text-align: center;
  padding: var(--dimension-3) var(--dimension-4);
  cursor: pointer;
  box-shadow: none;

  &:hover {
    background: var(--input-hover-bg-color);
  }
}

.cmk-time-picker__option--selected {
  background: var(--success);
  color: var(--font-color-light-bg);

  &:hover {
    background: var(--success-dimmed);
  }
}
</style>
