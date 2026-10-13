/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

/**
 * What to tell the operator about a failure.
 *
 * A message the server sent explains more than anything the SPA could say, so
 * it wins — it just is not translated, which is the price of being specific.
 * Anything that is not an error at all (a rejected promise carrying a string,
 * a network stack throwing something exotic) falls back to the caller's
 * sentence.
 */
export function errorText(error: unknown, fallback: TranslatedString): TranslatedString {
  return error instanceof Error && error.message ? untranslated(error.message) : fallback
}
