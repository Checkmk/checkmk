<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  CalendarDate,
  DateFormatter,
  type DateValue,
  getLocalTimeZone,
  today
} from '@internationalized/date'
import {
  DatePickerAnchor,
  DatePickerCalendar,
  DatePickerCell,
  DatePickerCellTrigger,
  DatePickerContent,
  DatePickerField,
  DatePickerGrid,
  DatePickerGridBody,
  DatePickerGridHead,
  DatePickerGridRow,
  DatePickerHeadCell,
  DatePickerHeader,
  DatePickerHeading,
  DatePickerInput,
  DatePickerNext,
  DatePickerPrev,
  DatePickerRoot,
  DatePickerTrigger
} from 'reka-ui'
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton'
import CmkIcon from '@/components/CmkIcon'
import ArrowDown from '@/components/graphics/ArrowDown.vue'

import CmkDeprecatedTimePicker from './CmkDeprecatedTimePicker.vue'
import { parseDateString } from './dateUtils'

const { mode = 'datetime' } = defineProps<{
  mode?: 'datetime' | 'date' | 'time'
  suffix?: string
}>()

const date = defineModel<string>('date', { required: true })
const time = defineModel<string>('time', { required: true })

const { _t } = usei18n()

const showDate = computed(() => mode === 'datetime' || mode === 'date')
const showTime = computed(() => mode === 'datetime' || mode === 'time')

const calendarDate = ref<DateValue | undefined>(
  date.value ? parseDateString(date.value) : undefined
)

const calendarPlaceholder = ref(calendarDate.value ?? today(getLocalTimeZone()))

watch(calendarDate, (newVal) => {
  if (newVal) {
    calendarPlaceholder.value = newVal
    date.value = newVal.toString()
    if (calendarOpen.value) {
      calendarOpen.value = false
    }
  }
})

watch(date, (newVal) => {
  if (newVal === calendarDate.value?.toString()) {
    return
  }
  const parsed = parseDateString(newVal)
  if (parsed) {
    calendarDate.value = parsed
  }
})

const longMonthFormatter = new DateFormatter('en-CA', { month: 'long' })
const shortMonthFormatter = new DateFormatter('en-CA', { month: 'short' })
const tz = getLocalTimeZone()

const displayMonthName = computed(() =>
  longMonthFormatter.format(calendarPlaceholder.value.toDate(tz))
)

const shortMonthNames = Array.from({ length: 12 }, (_, i) =>
  shortMonthFormatter.format(new CalendarDate(2024, i + 1, 1).toDate(tz))
)

type CalendarView = 'calendar' | 'month-picker'
const calendarView = ref<CalendarView>('calendar')
const calendarOpen = ref(false)

watch(calendarOpen, (isOpen) => {
  if (isOpen) {
    calendarView.value = 'calendar'
  }
})

function toggleMonthPicker() {
  calendarView.value = calendarView.value === 'month-picker' ? 'calendar' : 'month-picker'
}

function selectMonth(month: number) {
  calendarPlaceholder.value = calendarPlaceholder.value.set({ month })
  calendarView.value = 'calendar'
}

function shiftYear(delta: number) {
  calendarPlaceholder.value = calendarPlaceholder.value.set({
    year: calendarPlaceholder.value.year + delta
  })
}
</script>

<template>
  <span class="cmk-deprecated-date-time-picker">
    <!-- @vue-expect-error reka-ui DatePickerRoot types incompatible with exactOptionalPropertyTypes -->
    <DatePickerRoot
      v-if="showDate"
      v-model="calendarDate"
      v-model:placeholder="calendarPlaceholder"
      v-model:open="calendarOpen"
      :week-starts-on="1"
      :locale="'en-CA'"
      :prevent-deselect="true"
    >
      <DatePickerAnchor as="span" class="cmk-deprecated-date-time-picker__anchor">
        <DatePickerField
          v-slot="{ segments }"
          class="cmk-deprecated-date-time-picker__field"
          :aria-label="_t('Date')"
        >
          <template v-for="item in segments" :key="item.part">
            <DatePickerInput
              v-if="item.part !== 'literal'"
              :part="item.part"
              class="cmk-deprecated-date-time-picker__segment"
            >
              {{ item.value }}
            </DatePickerInput>
            <span v-else class="cmk-deprecated-date-time-picker__literal">{{ item.value }}</span>
          </template>
        </DatePickerField>
        <DatePickerTrigger
          class="cmk-deprecated-date-time-picker__trigger"
          :aria-label="_t('Open calendar')"
        >
          <CmkIcon name="insertdate" size="medium" />
        </DatePickerTrigger>
      </DatePickerAnchor>
      <DatePickerContent
        class="cmk-deprecated-date-time-picker__popover"
        align="start"
        :side-offset="4"
      >
        <DatePickerCalendar
          v-slot="{ weekDays, grid }"
          class="cmk-deprecated-date-time-picker__calendar"
        >
          <DatePickerHeader
            v-if="calendarView === 'calendar'"
            class="cmk-deprecated-date-time-picker__calendar-header"
          >
            <DatePickerPrev
              class="cmk-deprecated-date-time-picker__nav-btn"
              :aria-label="_t('Previous month')"
            >
              <ArrowDown
                class="cmk-deprecated-date-time-picker__nav-icon cmk-deprecated-date-time-picker__nav-icon--prev"
              />
            </DatePickerPrev>
            <DatePickerHeading class="cmk-deprecated-date-time-picker__calendar-heading">
              <CmkButton
                class="cmk-deprecated-date-time-picker__heading-toggle"
                variant="optional"
                :title="_t('Select month and year')"
                @click="toggleMonthPicker"
              >
                {{ displayMonthName }} {{ calendarPlaceholder.year }}
              </CmkButton>
            </DatePickerHeading>
            <DatePickerNext
              class="cmk-deprecated-date-time-picker__nav-btn"
              :aria-label="_t('Next month')"
            >
              <ArrowDown
                class="cmk-deprecated-date-time-picker__nav-icon cmk-deprecated-date-time-picker__nav-icon--next"
              />
            </DatePickerNext>
          </DatePickerHeader>
          <div
            v-if="calendarView === 'month-picker'"
            class="cmk-deprecated-date-time-picker__month-picker"
          >
            <div class="cmk-deprecated-date-time-picker__calendar-header">
              <CmkButton
                class="cmk-deprecated-date-time-picker__nav-btn"
                variant="optional"
                :title="_t('Previous year')"
                @click="shiftYear(-1)"
              >
                <ArrowDown
                  class="cmk-deprecated-date-time-picker__nav-icon cmk-deprecated-date-time-picker__nav-icon--prev"
                />
              </CmkButton>
              <span class="cmk-deprecated-date-time-picker__calendar-heading">{{
                calendarPlaceholder.year
              }}</span>
              <CmkButton
                class="cmk-deprecated-date-time-picker__nav-btn"
                variant="optional"
                :title="_t('Next year')"
                @click="shiftYear(1)"
              >
                <ArrowDown
                  class="cmk-deprecated-date-time-picker__nav-icon cmk-deprecated-date-time-picker__nav-icon--next"
                />
              </CmkButton>
            </div>
            <div class="cmk-deprecated-date-time-picker__month-grid">
              <CmkButton
                v-for="(name, index) in shortMonthNames"
                :key="index"
                class="cmk-deprecated-date-time-picker__month-option"
                :class="{
                  'cmk-deprecated-date-time-picker__month-option--selected':
                    index + 1 === calendarPlaceholder.month
                }"
                variant="optional"
                @click="selectMonth(index + 1)"
              >
                {{ name }}
              </CmkButton>
            </div>
          </div>
          <DatePickerGrid
            v-for="month in grid"
            v-show="calendarView === 'calendar'"
            :key="month.value.toString()"
          >
            <DatePickerGridHead>
              <DatePickerGridRow>
                <DatePickerHeadCell
                  v-for="day in weekDays"
                  :key="day"
                  class="cmk-deprecated-date-time-picker__head-cell"
                >
                  {{ day }}
                </DatePickerHeadCell>
              </DatePickerGridRow>
            </DatePickerGridHead>
            <DatePickerGridBody>
              <DatePickerGridRow
                v-for="(weekDates, index) in month.rows"
                :key="`weekDate-${index}`"
              >
                <DatePickerCell
                  v-for="weekDate in weekDates"
                  :key="weekDate.toString()"
                  :date="weekDate"
                >
                  <DatePickerCellTrigger
                    :day="weekDate"
                    :month="month.value"
                    class="cmk-deprecated-date-time-picker__cell-trigger"
                  />
                </DatePickerCell>
              </DatePickerGridRow>
            </DatePickerGridBody>
          </DatePickerGrid>
        </DatePickerCalendar>
      </DatePickerContent>
    </DatePickerRoot>

    <CmkDeprecatedTimePicker v-if="showTime" v-model="time" />

    <span v-if="suffix" class="cmk-deprecated-date-time-picker__suffix">
      {{ suffix }}
    </span>
  </span>
</template>

<!-- unscoped: reka-ui child components don't receive scoped data attributes -->
<style>
.cmk-deprecated-date-time-picker {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-4);
}

.cmk-deprecated-date-time-picker__anchor {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-4);
}

.cmk-deprecated-date-time-picker__field {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--dimension-3);
  padding: 1px 6px;
  background: var(--default-form-element-bg-color);
  color: var(--font-color);
  font-size: var(--font-size-small);
  line-height: 17px;
  height: var(--form-field-height);
  box-sizing: border-box;
  font-variant-numeric: tabular-nums;
}

.cmk-deprecated-date-time-picker__trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--dimension-3);
  padding: 0 var(--dimension-2);
  margin: 0;
  height: var(--form-field-height);
  background: transparent;
  cursor: pointer;
  box-shadow: none;
  opacity: 0.7;

  &:hover {
    opacity: 1;
  }

  &:focus-visible {
    opacity: 1;
    outline: revert;
  }
}

.cmk-deprecated-date-time-picker__segment {
  padding: 1px var(--dimension-2);
  border: none;
  border-radius: var(--dimension-2);
  outline: none;
  background: transparent;
  color: var(--font-color);
  font-variant-numeric: tabular-nums;
  height: auto;
  box-shadow: none;

  &:focus {
    background: var(--color-dark-blue-50);
    color: var(--white);
  }
}

.cmk-deprecated-date-time-picker__literal {
  color: var(--font-color-dimmed);
}

.cmk-deprecated-date-time-picker__popover {
  z-index: var(--z-index-modal-popup, 3500);
  background: var(--default-bg-color);
  border: 1px solid var(--default-border-color);
  border-radius: 6px;
  padding: var(--dimension-5);
  box-shadow: 0 var(--dimension-3) var(--dimension-5) rgb(0 0 0 / 15%);
  color: var(--font-color);
}

.cmk-deprecated-date-time-picker__calendar {
  font-size: 13px;
  color: var(--font-color);
  min-width: 260px;
}

.cmk-deprecated-date-time-picker__calendar button {
  color: var(--font-color);
}

.cmk-deprecated-date-time-picker__calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--dimension-4);
}

.cmk-deprecated-date-time-picker__calendar-heading {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  font-weight: 600;
  color: var(--font-color);
}

.cmk-deprecated-date-time-picker__heading-toggle {
  font-weight: 600;
  font-size: 13px;
  background: transparent;
  border: none;
  padding: var(--dimension-2) 6px;
  height: auto;

  &:hover {
    background: var(--input-hover-bg-color);
  }
}

.cmk-deprecated-date-time-picker__month-picker {
  margin-top: var(--dimension-3);
}

.cmk-deprecated-date-time-picker__month-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--dimension-3);
}

.cmk-deprecated-date-time-picker__month-option {
  height: var(--dimension-11);
  border: none;
  background: transparent;
  color: var(--font-color);
  font-size: 13px;
  font-weight: normal;
  padding: 0;

  &:hover {
    background: var(--input-hover-bg-color);
  }

  &.cmk-deprecated-date-time-picker__month-option--selected {
    background: var(--color-dark-blue-50);
    color: var(--white);
  }
}

.cmk-deprecated-date-time-picker__nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-9);
  height: var(--dimension-9);
  padding: 0;
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--dimension-3);
  background: var(--default-form-element-bg-color);
  color: var(--font-color);
  cursor: pointer;

  &:hover {
    background: var(--input-hover-bg-color);
  }
}

.cmk-deprecated-date-time-picker__nav-icon {
  flex-shrink: 0;
  width: 0.7em;
}

.cmk-deprecated-date-time-picker__nav-icon--prev {
  transform: rotate(90deg);
}

.cmk-deprecated-date-time-picker__nav-icon--next {
  transform: rotate(-90deg);
}

.cmk-deprecated-date-time-picker__head-cell {
  font-weight: 600;
  font-size: 12px;
  padding: var(--dimension-3) var(--dimension-4);
  text-align: center;
  color: var(--font-color-dimmed);
}

.cmk-deprecated-date-time-picker__cell-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-10);
  height: var(--dimension-10);
  border: none;
  border-radius: var(--dimension-3);
  background: transparent;
  color: var(--font-color);
  cursor: pointer;

  &:hover {
    background: var(--input-hover-bg-color);
  }

  &[data-selected] {
    background: var(--color-dark-blue-50);
    color: var(--white);
  }

  &[data-today] {
    font-weight: 700;
  }

  &[data-outside-view] {
    color: var(--font-color-dimmed);
  }

  &[data-disabled] {
    opacity: 0.3;
    cursor: default;
  }
}

.cmk-deprecated-date-time-picker__suffix {
  color: var(--font-color-dimmed);
  font-size: 12px;
}
</style>
