/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { describeFieldProblems } from '@/maps/utils/formValidation'

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

/**
 * What a rejected save says, for the operator rather than an API client: the
 * problems of a field the API names by its path, the detail of anything else,
 * and without naming the object when the text is shown at it already.
 */
export function saveFailureText(
  error: unknown,
  fallback: TranslatedString,
  objectId?: string
): TranslatedString {
  if (isConflict(error)) {
    return usei18n()._t('Someone else saved the map meanwhile.')
  }
  if (!(error instanceof CmkApiError) || typeof error.body !== 'object' || error.body === null) {
    return errorText(error, fallback)
  }
  const problems = describeFieldProblems(error.body)
  if (problems) {
    return untranslated(problems)
  }
  const { detail } = error.body as { detail?: unknown }
  if (typeof detail === 'string' && detail) {
    const own = objectId === undefined ? '' : `Object '${objectId}': `
    return untranslated(own && detail.startsWith(own) ? detail.slice(own.length) : detail)
  }
  return errorText(error, fallback)
}

/** Someone else saved the map since the version the save was made on. */
export function isConflict(failure: unknown): failure is CmkApiError {
  return failure instanceof CmkApiError && failure.statusCode === 412
}
