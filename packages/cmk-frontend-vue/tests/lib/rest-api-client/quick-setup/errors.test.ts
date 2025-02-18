/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkSimpleError } from '@/lib/error'
import { argumentError } from '@/lib/rest-api-client/errors'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'

const MULTIPLE_QUICK_SETUP_ACTIONS_RUNNING_ERROR = {
  title: 'Cannot start action',
  detail: 'Another Quick setup action already running.'
}

/**
 * This function creates a dummy AxiosError object for testing purposes
 *
 * @param data simulated received data
 * @returns AxiosError
 */
const _createAxiosError = (statusCode: number, statusText: string, data: unknown): AxiosError => {
  const err = new AxiosError(undefined, undefined, undefined, undefined, {
    status: statusCode,
    data: data,
    statusText: statusText,
    headers: {},
    config: undefined as unknown as InternalAxiosRequestConfig
  })
  return err
}

test('should return a CmkSimpleError instance when receiving status 429', async () => {
  const error = _createAxiosError(
    429,
    'Too Many Requests',
    MULTIPLE_QUICK_SETUP_ACTIONS_RUNNING_ERROR
  )
  const errorMessage = `${MULTIPLE_QUICK_SETUP_ACTIONS_RUNNING_ERROR.title}: ${MULTIPLE_QUICK_SETUP_ACTIONS_RUNNING_ERROR.detail}`

  const result = argumentError(error)

  expect(result).toBeInstanceOf(CmkSimpleError)
  expect(result.message).toBe(errorMessage)
})
