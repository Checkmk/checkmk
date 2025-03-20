/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { getUserFrontendConfig } from '@/lib/userConfig'

const mockCookie = vitest.fn()

beforeAll(() => {
  Object.defineProperty(document, 'cookie', {
    get: mockCookie
  })
})

beforeEach(() => {
  mockCookie.mockReturnValue('')
})

test('parses user config from cookie', async () => {
  mockCookie.mockReturnValue(
    'foo=bar; user_frontend_config=%7B%22dismissed_warnings%22%3A%20%5B%22notification_fallback%22%5D%7D; expires=Thu, 01 Jan 2170 00:00:00 GMT; baz=qux'
  )
  const result = getUserFrontendConfig()
  expect(result).toEqual({ dismissed_warnings: ['notification_fallback'] })
})
