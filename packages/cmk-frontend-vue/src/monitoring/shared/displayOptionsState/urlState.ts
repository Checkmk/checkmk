/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed } from 'vue'

import {
  DEFAULT_DISPLAY_OPTIONS,
  type DateFormatId,
  type DisplayOptions,
  type TimestampFormatId
} from '@/monitoring/shared/types'
import { readUrlState } from '@/monitoring/shared/urlState/readUrlState'
import type { Problem, UrlStateFormat, UrlStateWriter } from '@/monitoring/shared/urlState/types'

const NAME = 'display options'

const DATE_FORMAT_KEY = 'date_format'
const TIMESTAMP_FORMAT_KEY = 'timestamp_format'

/** Every param this slice claims, for `useUrlSync` to settle ownership with. */
export const DISPLAY_OPTIONS_KEYS: readonly string[] = [DATE_FORMAT_KEY, TIMESTAMP_FORMAT_KEY]

const DATE_FORMAT_IDS: readonly DateFormatId[] = [
  '%Y-%m-%d',
  '%d.%m.%Y',
  '%m/%d/%Y',
  '%d.%m.',
  '%m/%d'
]
const TIMESTAMP_FORMAT_IDS: readonly TimestampFormatId[] = ['mixed', 'abs', 'rel', 'both', 'epoch']

/**
 * The "Modify display options" choice as read from the URL. A field left
 * `undefined` means the URL said nothing usable about it - distinct from a
 * field at its default, which the codec already spells as an absent key -
 * so the caller can fall back to storage, then to {@link DEFAULT_DISPLAY_OPTIONS}.
 * A plain `Partial<DisplayOptions>` won't do under `exactOptionalPropertyTypes`:
 * that forbids assigning `undefined` to an optional key, exactly the value
 * "no opinion" needs to carry.
 */
export interface PartialDisplayOptions {
  dateFormat: DateFormatId | undefined
  timestampFormat: TimestampFormatId | undefined
}

interface RawDisplayOptions {
  dateFormat: string | undefined
  timestampFormat: string | undefined
}

function decode(params: URLSearchParams): RawDisplayOptions {
  return {
    dateFormat: params.get(DATE_FORMAT_KEY) ?? undefined,
    timestampFormat: params.get(TIMESTAMP_FORMAT_KEY) ?? undefined
  }
}

function reconcileField<T extends string>(
  raw: string | undefined,
  allowed: readonly T[],
  key: string,
  problems: Problem[]
): T | undefined {
  if (raw === undefined) {
    return undefined
  }
  if ((allowed as readonly string[]).includes(raw)) {
    return raw as T
  }
  problems.push({ dimension: key, message: `${key} named an unknown value (${raw}); ignored it` })
  return undefined
}

function reconcile(raw: RawDisplayOptions): { state: PartialDisplayOptions; problems: Problem[] } {
  const problems: Problem[] = []
  const state: PartialDisplayOptions = {
    dateFormat: reconcileField(raw.dateFormat, DATE_FORMAT_IDS, DATE_FORMAT_KEY, problems),
    timestampFormat: reconcileField(
      raw.timestampFormat,
      TIMESTAMP_FORMAT_IDS,
      TIMESTAMP_FORMAT_KEY,
      problems
    )
  }
  return { state, problems }
}

/**
 * `undefined` and "equal to the default" both mean the same thing to the URL -
 * omit the key - so this doubles as the encoder for a fully resolved
 * {@link DisplayOptions} (the writer's case) and for the partial, possibly
 * no-opinion state {@link reconcile} produces.
 */
function encode(state: PartialDisplayOptions): Record<string, string | null> {
  return {
    [DATE_FORMAT_KEY]:
      state.dateFormat === undefined || state.dateFormat === DEFAULT_DISPLAY_OPTIONS.dateFormat
        ? null
        : state.dateFormat,
    [TIMESTAMP_FORMAT_KEY]:
      state.timestampFormat === undefined ||
      state.timestampFormat === DEFAULT_DISPLAY_OPTIONS.timestampFormat
        ? null
        : state.timestampFormat
  }
}

/** How the "Modify display options" choice is spelled in the URL. */
export const displayOptionsFormat: UrlStateFormat<PartialDisplayOptions, RawDisplayOptions> = {
  name: NAME,
  keys: DISPLAY_OPTIONS_KEYS,
  codec: { encode, decode },
  reconcile
}

/**
 * Decodes the display options the URL currently names. Read once, before the
 * persisted ref exists - like {@link buildColumnStorageKey}'s column
 * visibility, a field the URL names wins over storage without being written
 * to it, so the user's own next change through the pane still persists.
 */
export function readDisplayOptionsFromUrl(search: string): PartialDisplayOptions {
  return readUrlState(displayOptionsFormat, search)
}

/**
 * Resolves what a persisted display-options ref should seed from: a field the
 * URL named wins over storage, per field - independent of one another, unlike
 * column visibility's single all-or-nothing list.
 */
export function seedDisplayOptions(
  fromUrl: PartialDisplayOptions,
  fromStorage: DisplayOptions
): DisplayOptions {
  return {
    dateFormat: fromUrl.dateFormat ?? fromStorage.dateFormat,
    timestampFormat: fromUrl.timestampFormat ?? fromStorage.timestampFormat
  }
}

/**
 * The "Modify display options" choice as a slice for `useUrlSync` to mirror,
 * matching `tableStateWriter`'s shape: it always reflects the live,
 * fully-resolved value, so a link shared mid-session carries the reader's
 * current choice rather than only what was true on page load.
 */
export function displayOptionsWriter(displayOptions: Ref<DisplayOptions>): UrlStateWriter {
  return {
    name: displayOptionsFormat.name,
    keys: displayOptionsFormat.keys,
    params: computed(() => displayOptionsFormat.codec.encode(displayOptions.value))
  }
}
