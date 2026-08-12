/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

export type SaveAction = 'retry' | 'reload' | 'overwrite'

export interface SaveFailure {
  message: TranslatedString
  actions: readonly SaveAction[]
  detail: TranslatedString | null
}

export interface SaveFailures {
  describeSaveFailure: (error: unknown) => SaveFailure
}

function failure(
  message: TranslatedString,
  actions: readonly SaveAction[],
  detail: TranslatedString | null = null
): SaveFailure {
  return { message, actions, detail }
}

function serverDetail(error: CmkApiError): TranslatedString {
  const context = error.getContext()
  return untranslated(context === '' ? error.message : `${error.message}\n\n${context}`)
}

export function useSaveFailures(): SaveFailures {
  const { _t } = usei18n()

  function describeSaveFailure(error: unknown): SaveFailure {
    if (!(error instanceof CmkApiError)) {
      return failure(_t('Could not reach the server. Your changes are still here.'), ['retry'])
    }
    switch (error.statusCode) {
      case 401:
        return failure(_t('Your session expired. Sign in again in another tab, then retry.'), [
          'retry'
        ])
      case 403:
        return failure(_t('You are no longer allowed to edit this graph.'), [])
      case 404:
        return failure(_t('This graph no longer exists.'), [])
      case 400:
        return failure(_t('The server rejected the graph definition.'), [], serverDetail(error))
      // A stale If-Match cannot succeed on a retry: the etag only advances on a save that worked.
      case 412:
        return failure(
          _t('This graph changed since you opened it.'),
          ['reload', 'overwrite'],
          _t(
            'Reload to use the newer graph and discard your unsaved changes, or overwrite to keep your changes and replace the newer one.'
          )
        )
      default:
        return failure(
          _t('The server could not save the graph. Your changes are still here.'),
          ['retry'],
          serverDetail(error)
        )
    }
  }

  return { describeSaveFailure }
}
