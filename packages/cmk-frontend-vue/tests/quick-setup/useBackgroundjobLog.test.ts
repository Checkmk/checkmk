/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useBackgroundJobLog } from '@/quick-setup/components/BackgroundJobLog'
import type { LogUpdate } from '@/quick-setup/components/BackgroundJobLog/useBackgroundJobLog'

const DUMMY_LOG: LogUpdate = {
  steps: [{ title: 'Parse the connection configuration data', status: 'active', index: 0 }]
}

test('should be empty when created', async () => {
  const { isEmpty, count } = useBackgroundJobLog()
  expect(isEmpty()).toBe(true)
  expect(count()).toBe(0)
})

test('should add data', async () => {
  const { update, isEmpty, count } = useBackgroundJobLog()

  expect(count()).toBe(0)
  expect(isEmpty()).toBe(true)
  update(DUMMY_LOG)
  expect(count()).toBe(1)
  expect(isEmpty()).toBe(false)
})

test('should clear the internal data', async () => {
  const { count, update, clear } = useBackgroundJobLog()

  update(DUMMY_LOG)
  expect(count()).toBe(1)

  clear()
  expect(count()).toBe(0)
})

test('should count the actual entries', async () => {
  const { isEmpty, count, update, clear } = useBackgroundJobLog()

  update(DUMMY_LOG)
  expect(isEmpty()).toBe(false)
  expect(count()).toBe(1)

  clear()
  expect(isEmpty()).toBe(true)
  expect(count()).toBe(0)
})

test('should update data', async () => {
  const { update, count, entries } = useBackgroundJobLog()

  const payload: LogUpdate = JSON.parse(JSON.stringify(DUMMY_LOG))

  update(payload)
  expect(count()).toBe(1)

  expect(entries.value[0]!.title).toBe('Parse the connection configuration data')
  expect(entries.value[0]!.status).toBe('active')

  payload.steps[0]!.status = 'completed'
  update(payload)
  expect(count()).toBe(1)
  expect(entries.value[0]!.status).toBe('completed')
})

test('shoud check if task is active', async () => {
  const { update, isTaskActive } = useBackgroundJobLog()
  const payload: LogUpdate = JSON.parse(JSON.stringify(DUMMY_LOG))
  update(payload)
  expect(isTaskActive()).toBe(true)

  payload.steps[0]!.status = 'completed'
  update(payload)
  expect(isTaskActive()).toBe(false)
})

test('shoud set active taks to error', async () => {
  const { update, isTaskActive, setActiveTasksToError, entries } = useBackgroundJobLog()

  update(DUMMY_LOG)
  expect(isTaskActive()).toBe(true)

  setActiveTasksToError()
  expect(isTaskActive()).toBe(false)
  expect(entries.value[0]!.status).toBe('error')
})

test('should stop waiting on error', async () => {
  const { update, setActiveTasksToError, isRunning } = useBackgroundJobLog(true)

  expect(isRunning.value).toBe(false)

  update(DUMMY_LOG)
  expect(isRunning.value).toBe(true)

  setActiveTasksToError()
  expect(isRunning.value).toBe(false)
})

test('should never be running', async () => {
  const { update, setActiveTasksToError, isRunning } = useBackgroundJobLog()

  expect(isRunning.value).toBe(false)

  update(DUMMY_LOG)
  expect(isRunning.value).toBe(false)

  setActiveTasksToError()
  expect(isRunning.value).toBe(false)
})
