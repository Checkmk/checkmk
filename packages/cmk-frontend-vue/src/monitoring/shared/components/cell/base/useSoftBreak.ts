/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type MaybeRefOrGetter, computed, toValue } from 'vue'

const SOFT_BREAK_CHARS = /([ \-_.])/g
const ZERO_WIDTH_SPACE = '​'

/**
 * Insert zero-width spaces so long, otherwise unbreakable cell text can wrap.
 *
 * Break opportunities are added after every space, hyphen, underscore and dot;
 * runs without any of those separators fall back to a break every
 * `hardBreakEvery` characters.
 */
export function softBreak(text: string, hardBreakEvery: number = 15): string {
  const hardBreak = new RegExp(`([^\\s\\-_.]{${hardBreakEvery}})`, 'g')
  return text
    .replace(SOFT_BREAK_CHARS, `$1${ZERO_WIDTH_SPACE}`)
    .replace(hardBreak, `$1${ZERO_WIDTH_SPACE}`)
}

/** {@link softBreak} over reactive text. */
export function useSoftBreak(
  text: MaybeRefOrGetter<string>,
  hardBreakEvery: MaybeRefOrGetter<number> = 15
): ComputedRef<string> {
  return computed(() => softBreak(toValue(text), toValue(hardBreakEvery)))
}
