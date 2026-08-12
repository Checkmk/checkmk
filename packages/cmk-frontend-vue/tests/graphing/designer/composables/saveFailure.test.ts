/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'

import { useSaveFailures } from '@/graphing/designer/composables/saveFailure'

const { describeSaveFailure } = useSaveFailures()

function apiError(status: number, message = 'Title: detail', context = ''): CmkApiError {
  return new CmkApiError(message, null, context, status)
}

test('an unreachable server keeps the changes and offers a retry', () => {
  expect(describeSaveFailure(new TypeError('Failed to fetch'))).toMatchObject({
    actions: ['retry'],
    message: 'Could not reach the server. Your changes are still here.'
  })
})

test('a conflict offers a reload and says what that costs', () => {
  const failure = describeSaveFailure(apiError(412))

  expect(failure.actions).toEqual(['reload'])
  expect(failure.message).toBe('This graph changed since you opened it.')
  expect(failure.detail).toContain('discards your unsaved changes')
})

test('a conflict never offers a retry, which would re-send the same stale version', () => {
  expect(describeSaveFailure(apiError(412)).actions).not.toContain('retry')
})

test('an expired session can be recovered without losing the edits', () => {
  expect(describeSaveFailure(apiError(401)).actions).toEqual(['retry'])
})

test('a lost permission and a deleted graph offer nothing', () => {
  expect(describeSaveFailure(apiError(403))).toMatchObject({ actions: [] })
  expect(describeSaveFailure(apiError(404))).toMatchObject({ actions: [] })
})

test('a rejected definition quotes the server and keeps the crash report', () => {
  const failure = describeSaveFailure(
    apiError(400, 'Bad Request: ids must be unique', 'Crash report: http://crash/1')
  )

  expect(failure.actions).toEqual([])
  expect(failure.detail).toContain('Bad Request: ids must be unique')
  expect(failure.detail).toContain('Crash report: http://crash/1')
})

test('a server error keeps the changes and reports the same way', () => {
  const failure = describeSaveFailure(apiError(500, 'boom', 'Crash report: http://crash/1'))

  expect(failure.actions).toEqual(['retry'])
  expect(failure.detail).toContain('boom')
  expect(failure.detail).toContain('Crash report: http://crash/1')
})
