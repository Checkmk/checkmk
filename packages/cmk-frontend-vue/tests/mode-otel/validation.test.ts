/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { isValidPasswordIdForEnvVar } from '@/mode-otel/otel-configuration-steps/validation'

describe('isValidPasswordIdForEnvVar', () => {
  it.each(['pw1', 'PW_1', 'a_b_c', 'A', '_', '_pw', '_1'])('accepts %s', (id) =>
    expect(isValidPasswordIdForEnvVar(id)).toBe(true)
  )
  it.each([
    ['empty', ''],
    ['leading digit', '0123'],
    ['leading digit', '1abc'],
    ['hyphen', 'pw-1'],
    ['space', 'pw 1'],
    ['dot', 'pw.1'],
    ['slash', 'pw/1'],
    ['colon', 'pw:1'],
    ['non-ascii', 'päss'],
    ['dollar', 'pw$'],
    ['plus', 'pw+1']
  ])('rejects %s (%s)', (_desc, id) => expect(isValidPasswordIdForEnvVar(id)).toBe(false))
})
