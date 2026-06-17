/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CalendarDate, ZonedDateTime } from '@internationalized/date'

import type { TranslatedString } from '@/lib/i18nString'

/**
 * A quick-select range offered by `CmkTimeRangePicker`. `getRange` is evaluated lazily on
 * selection, so relative ranges (e.g. "Today") reflect the current time. `id` must be stable and
 * must not be `'custom'` — that id is reserved for the auto-appended "Custom" (manual range) entry.
 */
export interface RangePreset {
  id: string
  label: TranslatedString
  getRange: () => DateTimeRange
}

/**
 * A fully-populated date & time range. Both endpoints are always present; a nullable range is
 * represented as `DateTimeRange | null` — never a half-empty range (one endpoint set, the other not).
 */
export interface DateTimeRange {
  from: ZonedDateTime
  to: ZonedDateTime
}

/** A clock time, timezone-free. `hour` is always 0-23 (canonical) regardless of display cycle. */
export interface TimeValue {
  hour: number
  minute: number
}

/** A complete wall-clock date + time. */
export interface DateTimeParts {
  date: CalendarDate
  time: TimeValue
}

/** The editable date + time draft. Each half is `null` while that field is empty or partial. */
export interface DateTimePartsDraft {
  date: CalendarDate | null
  time: TimeValue | null
}

/** The range picker's staged endpoints. Each endpoint is a {@link DateTimePartsDraft}. */
export interface RangeDraft {
  from: DateTimePartsDraft
  to: DateTimePartsDraft
}

/** Meridiem-based (12-hour AM/PM) display cycles. h12 shows the noon/midnight slot as `12`; h11
 * shows it as `0`, so its hours run `0..11` instead of `1..12`. */
export type MeridiemCycle = 11 | 12

/** Display cycle for the time inputs: a meridiem cycle (h11/h12), or 24-hour. */
export type HourCycle = MeridiemCycle | 24

/** Meridiem marker used in 12-hour display. */
export type Meridiem = 'AM' | 'PM'

/** Day of the week, 0 = Sunday … 6 = Saturday (matches JS `Date.getDay()`). */
export type Weekday = 0 | 1 | 2 | 3 | 4 | 5 | 6

/** Localized weekday names, keyed by absolute weekday (0 = Sunday … 6 = Saturday). */
export type WeekdayNames = Record<Weekday, TranslatedString>

/** Which section of a date a segment represents. */
export type DateSectionType = 'day' | 'month' | 'year'

/** How a date is laid out: the order of its sections and the literal separator between them. */
export interface DateFormatParts {
  order: DateSectionType[]
  separator: string
}

/** Source for the date display format. */
export type DateFormatKind = 'locale' | 'iso'

/** Display width for localized month names. */
export type MonthNameStyle = 'long' | 'short'

/** Display width for localized weekday names. */
export type WeekdayNameStyle = 'narrow' | 'short' | 'long'

/**
 * The full bundle of user-facing display settings shared by the date/time pickers. Each field
 * falls back to the browser locale when omitted. `timeZone` is deliberately not part of this —
 * it changes which instant a value represents (unix↔zoned conversion), not just its display,
 * and is therefore a separate prop on the pickers that deal in instants (it never reaches the
 * wall-clock input components at all).
 */
export interface DateTimeSettings {
  dateFormat: DateFormatKind
  hourCycle: HourCycle
  firstDayOfWeek: Weekday
  weekendDays: Weekday[]
}

/**
 * Per-picker settings props: each picker only offers the fields it actually uses, while a wider
 * settings bundle (e.g. `Partial<DateTimeSettings>` derived from user configuration) stays
 * assignable to all of them — extra fields are simply ignored.
 */
export type DatePickerSettings = Partial<
  Pick<DateTimeSettings, 'dateFormat' | 'firstDayOfWeek' | 'weekendDays'>
>
export type TimePickerSettings = Partial<Pick<DateTimeSettings, 'hourCycle'>>
export type DateTimePickerSettings = Partial<DateTimeSettings>

/**
 * Locale-derived settings, resolved once (e.g. in a composite picker) and passed down to the
 * presentational primitives so those stay free of `Intl` / locale concerns and remain testable.
 */
export interface ResolvedDateTimeSettings {
  hourCycle: HourCycle
  firstDayOfWeek: Weekday
  weekendDays: Weekday[]
  dateFormat: DateFormatParts
  /** Short month names (what the calendar controls' dropdown renders). */
  monthNamesShort: TranslatedString[]
  /** Full month names (e.g. the calendar grid's spoken `aria-label`, "June 2026"). */
  monthNamesLong: TranslatedString[]
  /** Narrow weekday names (what the calendar grid header renders). */
  weekdayNamesNarrow: WeekdayNames
  /** Short weekday names (e.g. the From/To labels in the range picker). */
  weekdayNamesShort: WeekdayNames
  /** Full weekday names (e.g. the spoken `aria-label` for the grid's column headers). */
  weekdayNamesLong: WeekdayNames
  /** IANA timezone used for calendar derivation and unix↔typed conversion (e.g. `"Europe/Berlin"`). */
  timeZone: string
  /** Locale-formatted "month year" for spoken labels (e.g. `"June 2026"`); ordering follows locale. */
  formatMonthYear: (date: CalendarDate) => TranslatedString
  /** Locale-formatted long date without weekday for spoken labels (e.g. `"June 10, 2026"`). */
  formatLongDate: (date: CalendarDate) => TranslatedString
}

/**
 * The `save` slot shared by the date/time flyout footer and the pickers that forward to it.
 * Intersect with a component's own slots to extend it, e.g.
 * `defineSlots<DateTimeSaveSlots & { trigger?: ... }>()` — keeping the doc on `save` intact.
 */
export interface DateTimeSaveSlots {
  /** Content shown next to the Save checkbox in the footer; only rendered in save mode. */
  save?: () => unknown
}

/**
 * Apply-in-place ("Save") configuration shared by the date, date-time and range pickers. The
 * footer shows the save slot behind a checkbox; `saveHandler` runs on Apply while it is checked.
 */
export interface DateTimeSaveModeProps {
  /** Show the Save checkbox in the footer; without it the picker only applies to its model. */
  saveMode?: boolean
  /** Label shown next to the Save checkbox; defaults to a per-picker string. */
  saveLabel?: TranslatedString | undefined
  /** Run on Apply while Save is checked; return `false` to reject the apply (and keep the flyout open). */
  saveHandler?: (() => boolean | Promise<boolean>) | undefined
}

/** Props for `CmkDatePicker`. `Nullable` decides whether the value may be cleared. */
export interface CmkDatePickerProps<
  Nullable extends boolean = false
> extends DateTimeSaveModeProps {
  /** Display overrides; each field falls back to the browser locale. Extra fields from a wider
   * settings bundle are ignored. */
  settings?: DatePickerSettings | undefined
  /** IANA timezone used only to decide which calendar day is highlighted as "today"; the picked
   * value is a timezone-free date and is unaffected. Defaults to the browser zone. */
  timeZone?: string | undefined
  /** Allow clearing the value. This is static configuration and must not change ad hoc after mount. */
  nullable?: Nullable
  /** Render the trigger non-interactive and prevent the flyout from opening. */
  disabled?: boolean
  /** Accessible name for the popup dialog (sets `aria-label`). */
  label?: TranslatedString | undefined
}

/** Props for `CmkDateTimePicker`. `Nullable` decides whether the value may be cleared. */
export interface CmkDateTimePickerProps<
  Nullable extends boolean = false
> extends DateTimeSaveModeProps {
  /** Display overrides; each field falls back to the browser locale. Extra fields from a wider
   * settings bundle are ignored. */
  settings?: DateTimePickerSettings | undefined
  /** IANA timezone for converting the selected wall-clock date & time to/from the `ZonedDateTime`
   * value. Defaults to the browser zone. */
  timeZone?: string | undefined
  /** Allow clearing the value. This is static configuration and must not change ad hoc after mount. */
  nullable?: Nullable
  /** Render the trigger non-interactive and prevent the flyout from opening. */
  disabled?: boolean
  /** Accessible name for the popup dialog (sets `aria-label`). */
  label?: TranslatedString | undefined
}

/** Props for `CmkTimePicker`. A bare wall-clock time has no "save in place" semantics, so this
 * picker intentionally omits the save-mode props. `Nullable` decides whether it may be cleared. */
export interface CmkTimePickerProps<Nullable extends boolean = false> {
  /** Display overrides; each field falls back to the browser locale. Extra fields from a wider
   * settings bundle are ignored. */
  settings?: TimePickerSettings | undefined
  /** Allow clearing the value. This is static configuration and must not change ad hoc after mount. */
  nullable?: Nullable
  /** Render the trigger non-interactive and prevent the flyout from opening. */
  disabled?: boolean
  /** Accessible name for the popup dialog (sets `aria-label`). */
  label?: TranslatedString | undefined
}

/** Props for `CmkTimeRangePicker`. `Nullable` decides whether either endpoint may be cleared. */
export interface CmkTimeRangePickerProps<
  Nullable extends boolean = false
> extends DateTimeSaveModeProps {
  /** Display overrides; each field falls back to the browser locale. Extra fields from a wider
   * settings bundle are ignored. */
  settings?: DateTimePickerSettings | undefined
  /** IANA timezone for converting each endpoint's wall-clock date & time to/from its
   * `ZonedDateTime` value. Defaults to the browser zone. */
  timeZone?: string | undefined
  /** Allow clearing the range (set it to `null`). A range is always both endpoints or `null`, never
   * half-empty. This is static configuration and must not change ad hoc after mount. */
  nullable?: Nullable
  /** IANA timezone of the server; the displayed server time is derived from the browser
   * clock in that zone (and ticks while the flyout is open). */
  serverTimeZone?: string | undefined
  /**
   * Quick-select ranges shown as a single-choice list beside the calendars. When provided, a
   * "Custom" entry is appended automatically and selected whenever the range is edited by hand.
   */
  presets?: RangePreset[] | undefined
  /** Render the trigger non-interactive and prevent the flyout from opening. */
  disabled?: boolean
  /** Accessible name for the popup dialog (sets `aria-label`). */
  label?: TranslatedString | undefined
}
