/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type ComputedRef,
  type MaybeRefOrGetter,
  type Ref,
  computed,
  shallowRef,
  toValue,
  watch
} from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import { focusLeftElement } from '../../focusLeftElement'
import { useSegmentFocus } from './useSegmentFocus'

/** The single editing representation: each segment's visible string, keyed by segment. */
export type SegmentText = Record<string, string>

/** One input segment, pure data. `pad: null` marks a read-only cycling segment (the meridiem). */
export interface Segment {
  key: string
  ariaLabel: TranslatedString
  /** Minimum width in `ch` units. */
  widthCh: number
  /** Number of digits to accept, or `null` for a read-only segment. */
  pad: number | null
  placeholder: string
  /** Separator rendered before this segment, overriding the field default (ignored on the first). */
  separatorBefore?: string
  /** Width-reservation variants for the read-only segment (e.g. `['AM', 'PM']`); `[]` for digit segments. */
  options: string[]
  /** Spoken `aria-valuetext` for the segment's current text (month `"06"` → `"June"`); `undefined`
   *  falls back to the numeric `aria-valuenow`. Omit for plain numeric segments. */
  valueText?: (text: string) => TranslatedString | undefined
}

/**
 * Everything {@link useSegmentedField} needs to drive one field type. Every function speaks in
 * display strings ({@link SegmentText}); the engine never knows what a date or a time is.
 */
export interface FieldType<T> {
  segments: Segment[]
  separator: string
  /** Model → display strings. `prev` keeps sticky display state (e.g. the meridiem while empty). */
  toText: (value: T | null, prev: SegmentText) => SegmentText
  /** Display strings → model; `null` while the segments do not form a complete, valid value. */
  toValue: (text: SegmentText) => T | null
  /** Bring the segments into canonical display form: pad, clamp, snap the day to its month. */
  normalize: (text: SegmentText) => SegmentText
  /** Step one segment by a unit (real clock/calendar arithmetic), carrying into the owner if it overflows. */
  step: (text: SegmentText, key: string, delta: 1 | -1) => { text: SegmentText; carry?: -1 | 1 }
  /** Whether the typed digits cannot usefully grow (triggers auto-advance). */
  isComplete: (key: string, digits: string) => boolean
  /** Select an option on a read-only segment by its first character; `undefined` when not consumed. */
  typeChar: (text: SegmentText, key: string, char: string) => SegmentText | undefined
  /** Numeric spinbutton bounds (`aria-valuemin`/`max`) for a segment, given the whole field's text so
   *  context-dependent ranges work (the day's max follows month/year). `undefined` for the meridiem. */
  bounds?: (key: string, text: SegmentText) => { min: number; max: number } | undefined
}

/** A single segment, fully resolved for the template — it carries no field knowledge. */
export interface SegmentView {
  key: string
  ariaLabel: TranslatedString
  widthCh: number
  /** Effective separator rendered before this segment (`''` for the first). */
  separator: string
  /** Buffer digits while focused, otherwise the rendered value. */
  text: string
  /** A digit segment (`inputmode="numeric"`); `false` is the read-only meridiem. */
  editable: boolean
  maxlength: number
  placeholder: string
  options: string[]
  /** Spinbutton `aria-valuenow`: the current numeric value, or `undefined` when empty / non-numeric. */
  valueNow: number | undefined
  /** Spinbutton `aria-valuemin`; `undefined` for the non-numeric meridiem. */
  valueMin: number | undefined
  /** Spinbutton `aria-valuemax`; `undefined` for the non-numeric meridiem. */
  valueMax: number | undefined
  /** Spinbutton `aria-valuetext`: spoken value ("June"/"PM"/"Empty"), or `undefined` to use `valueNow`. */
  valueText: TranslatedString | undefined
}

export interface SegmentedFieldApi {
  views: ComputedRef<SegmentView[]>
  /** Whether the field is empty, partially filled (incomplete), or a complete value — for `aria-invalid`. */
  state: ComputedRef<'empty' | 'partial' | 'complete'>
  registerInput: (key: string, el: HTMLInputElement | null) => void
  onInput: (key: string, event: Event) => void
  onKey: (key: string, event: KeyboardEvent) => void
  onBlur: () => void
  onFieldFocusOut: (event: FocusEvent) => void
  focus: () => void
  focusLast: () => void
}

/** Clamp `value` into `[min, max]`. */
export function clampToRange(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

/** Map any integer cyclically into `[min, max]` (e.g. an hour of 24 → 0, −1 → 23). The first
 *  `% span` can be negative when `value < min`; adding `span` and taking `% span` again forces a
 *  non-negative remainder before shifting back by `min`. */
export function wrapToRange(value: number, min: number, max: number): number {
  const span = max - min + 1
  return ((((value - min) % span) + span) % span) + min
}

/** A digit segment can no longer usefully grow: it already holds the max number of digits, or
 *  multiplying by ten would exceed the segment's max (so the next typed digit could only overflow).
 *  Triggers auto-advance to the next segment. */
export function digitsAreComplete(digits: string, maxlen: number, max: number): boolean {
  return digits.length >= maxlen || parseInt(digits, 10) * 10 > max
}

/** Parse a segment string to a number, or `null` when it is empty. */
export function parseSegment(value: string): number | null {
  return value === '' ? null : parseInt(value, 10)
}

/** Zero-pad a number to `width` digits. */
export function padNumber(value: number, width: number): string {
  return value.toString().padStart(width, '0')
}

/** Select the entire contents of the focused input (so the next keystroke overwrites). */
export function selectInputOnFocus(event: FocusEvent): void {
  ;(event.target as HTMLInputElement | null)?.select()
}

export function useSegmentedField<T>(
  fieldType: MaybeRefOrGetter<FieldType<T>>,
  model: Ref<T | null>,
  callbacks: {
    commit: () => void
    navigateOut?: (direction: -1 | 1) => void
    carry?: (days: -1 | 1) => void
  }
): SegmentedFieldApi {
  const spec = (): FieldType<T> => toValue(fieldType)
  const { _t } = usei18n()
  const emptyLabel = _t('Empty')

  const text = shallowRef<SegmentText>(spec().toText(model.value, {}))
  // Whether the focused segment holds uncommitted keystrokes (folded in on blur / navigation).
  let dirty = false
  // The exact value object we last wrote, to ignore the v-model echoing it back at us.
  let lastWritten: T | null | undefined

  const focus = useSegmentFocus(
    () => spec().segments.map((segment) => segment.key),
    (direction) => callbacks.navigateOut?.(direction)
  )

  watch(model, (value) => {
    if (value === lastWritten) {
      return
    }
    text.value = spec().toText(value, text.value)
    dirty = false
  })

  // A format / hour-cycle change re-derives the display (e.g. 24h → 12h splits out the meridiem).
  watch(
    () => spec(),
    (next) => {
      text.value = next.toText(model.value, text.value)
      dirty = false
    }
  )

  /** Normalize the segments for display and push the derived value to the model. */
  function commit(next: SegmentText): void {
    const normalized = spec().normalize(next)
    text.value = normalized
    lastWritten = spec().toValue(normalized)
    model.value = lastWritten
    dirty = false
  }

  function flushIfDirty(): void {
    if (dirty) {
      commit(text.value)
    }
  }

  const views = computed<SegmentView[]>(() => {
    const field = spec()
    return field.segments.map((segment, index) => {
      const segmentText = text.value[segment.key] ?? ''
      const numeric = segment.pad !== null
      const isEmpty = segmentText === ''
      // `valueNow`/`bounds` are digit-segment only; the meridiem is a value-text-only spinbutton.
      const valueNow = numeric && !isEmpty ? (parseSegment(segmentText) ?? undefined) : undefined
      const bounds = numeric ? field.bounds?.(segment.key, text.value) : undefined
      // Empty reads "Empty"; otherwise the segment's spoken name, else the numeric value.
      const valueText = isEmpty ? emptyLabel : segment.valueText?.(segmentText)
      return {
        key: segment.key,
        ariaLabel: segment.ariaLabel,
        widthCh: segment.widthCh,
        separator: index === 0 ? '' : (segment.separatorBefore ?? field.separator),
        text: segmentText,
        editable: numeric,
        maxlength: segment.pad ?? 2,
        placeholder: segment.placeholder,
        options: segment.options,
        valueNow,
        valueMin: bounds?.min,
        valueMax: bounds?.max,
        valueText
      }
    })
  })

  // `empty` when no digit segment carries text, `complete` when the segments form a valid value,
  // `partial` otherwise — the last drives `aria-invalid` for a half-entered field.
  const state = computed<'empty' | 'partial' | 'complete'>(() => {
    const field = spec()
    const filled = field.segments.some(
      (segment) => segment.pad !== null && (text.value[segment.key] ?? '') !== ''
    )
    if (!filled) {
      return 'empty'
    }
    return field.toValue(text.value) !== null ? 'complete' : 'partial'
  })

  function segmentFor(key: string): Segment | undefined {
    return spec().segments.find((segment) => segment.key === key)
  }

  function onInput(key: string, event: Event): void {
    const segment = segmentFor(key)
    if (segment === undefined || segment.pad === null) {
      return
    }
    const digits = (event.target as HTMLInputElement).value.replace(/\D/g, '').slice(0, segment.pad)
    text.value = { ...text.value, [key]: digits }
    dirty = true
    if (digits !== '' && spec().isComplete(key, digits)) {
      commit(text.value)
      focus.moveFocus(key, 1)
    }
  }

  function onArrow(key: string, delta: 1 | -1): void {
    // Fold any pending digits first, so the step works on a normalized value (e.g. a typed 12h "15"
    // becomes "03 PM" before being stepped), then step the canonical value.
    flushIfDirty()
    const result = spec().step(text.value, key, delta)
    commit(result.text)
    if (result.carry !== undefined) {
      callbacks.carry?.(result.carry)
    }
  }

  function onKey(key: string, event: KeyboardEvent): void {
    const field = spec()
    switch (event.key) {
      case 'Enter':
        event.preventDefault()
        // Not dirty ⇒ `text` is already normalized (after every commit, the model watch's toText,
        // an arrow step, or a field focus-out), so flushing a pending edit is all that's needed.
        flushIfDirty()
        callbacks.commit()
        return
      case 'ArrowUp':
        event.preventDefault()
        onArrow(key, 1)
        return
      case 'ArrowDown':
        event.preventDefault()
        onArrow(key, -1)
        return
      case 'ArrowLeft':
        event.preventDefault()
        flushIfDirty()
        focus.moveFocus(key, -1)
        return
      case 'ArrowRight':
        event.preventDefault()
        flushIfDirty()
        focus.moveFocus(key, 1)
        return
    }
    if (event.key === field.separator) {
      event.preventDefault()
      flushIfDirty()
      focus.moveFocus(key, 1)
      return
    }
    const segment = segmentFor(key)
    if (segment !== undefined && segment.pad === null && event.key.length === 1) {
      const next = field.typeChar(text.value, key, event.key)
      if (next !== undefined) {
        event.preventDefault()
        commit(next)
      }
    }
  }

  function onBlur(): void {
    flushIfDirty()
  }

  /** Focus leaving the whole field reformats the display (the leaving segment's blur already committed). */
  function onFieldFocusOut(event: FocusEvent): void {
    if (focusLeftElement(event)) {
      text.value = spec().normalize(text.value)
    }
  }

  return {
    views,
    state,
    registerInput: focus.registerInput,
    onInput,
    onKey,
    onBlur,
    onFieldFocusOut,
    focus: focus.focusFirst,
    focusLast: focus.focusLast
  }
}
