/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { expect, test } from 'vitest'

import { useAPILoader } from '@/dashboard/composables/api/useAPILoader'

/** Records how often the loader asked for data, and what to answer with. */
function recordingFetcher<T>(...answers: Array<T | Error>) {
  const calls: number[] = []
  const fetcher = async (): Promise<T> => {
    const answer = answers[Math.min(calls.length, answers.length - 1)]!
    calls.push(calls.length)
    if (answer instanceof Error) {
      throw answer
    }
    return answer
  }
  return { fetcher, callCount: () => calls.length }
}

test('the fetched data becomes the loader state', async () => {
  const { fetcher } = recordingFetcher({ value: ['a'] })
  const loader = useAPILoader<{ value: string[] }>({ fetcher })

  await loader.ensureLoaded()

  expect(loader.state.value).toEqual({ value: ['a'] })
  expect(loader.error.value).toBeNull()
})

test('a second ensureLoaded serves the data already held', async () => {
  const { fetcher, callCount } = recordingFetcher({ value: ['a'] })
  const loader = useAPILoader<{ value: string[] }>({ fetcher })

  await loader.ensureLoaded()
  await loader.ensureLoaded()

  expect(callCount()).toBe(1)
})

test('a rejected fetch surfaces the message and leaves the data unset', async () => {
  const { fetcher } = recordingFetcher<{ value: string[] }>(
    new CmkApiError('Forbidden: you may not read this', null, '', 403)
  )
  const loader = useAPILoader<{ value: string[] }>({ fetcher })

  await loader.ensureLoaded()

  expect(loader.error.value).toBe('Forbidden: you may not read this')
  expect(loader.state.value).toBeNull()
})

test('ensureLoaded asks again after a failed load', async () => {
  const { fetcher, callCount } = recordingFetcher<{ value: string[] }>(new Error('boom'))
  const loader = useAPILoader<{ value: string[] }>({ fetcher })

  await loader.ensureLoaded()
  await loader.ensureLoaded()

  expect(callCount()).toBe(2)
})

test('a load that succeeds after a failure clears the error', async () => {
  const { fetcher } = recordingFetcher<{ value: string[] }>(new Error('boom'), { value: ['a'] })
  const loader = useAPILoader<{ value: string[] }>({ fetcher })

  await loader.ensureLoaded()
  await loader.ensureLoaded()

  expect(loader.error.value).toBeNull()
  expect(loader.state.value).toEqual({ value: ['a'] })
})

test('previously loaded data survives a failing refresh', async () => {
  const { fetcher } = recordingFetcher<{ value: string[] }>({ value: ['a'] }, new Error('boom'))
  const loader = useAPILoader<{ value: string[] }>({ fetcher })

  await loader.ensureLoaded()
  await loader.refresh()

  expect(loader.state.value).toEqual({ value: ['a'] })
  expect(loader.error.value).toBe('boom')
})
