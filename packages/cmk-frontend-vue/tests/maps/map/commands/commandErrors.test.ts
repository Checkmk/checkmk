/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import { describeGroupCommandError, messageOf } from '@/maps/map/commands/commandErrors'

type TranslateFn = ReturnType<typeof usei18n>['_t']

const _t: TranslateFn = (message: string, params?: Record<string, string | number>) =>
  untranslated(
    params ? message.replace(/%\{(\w+)\}/g, (_, key: string) => String(params[key])) : message
  )

describe('messageOf', () => {
  it("takes an error's own message", () => {
    expect(messageOf(new Error('Checkmk said no'), 'fallback')).toBe('Checkmk said no')
  })

  it('falls back for a thrown error with an empty message', () => {
    expect(messageOf(new Error(''), 'fallback')).toBe('fallback')
  })

  it('falls back for anything that is not an error at all', () => {
    expect(messageOf({ status: 500 }, 'fallback')).toBe('fallback')
  })
})

describe('describeGroupCommandError', () => {
  const tipFor = (message: string, isGroup: boolean) =>
    describeGroupCommandError(message, isGroup, 'host group', _t)

  it('explains the implicit-group rejection, which reads like a bug otherwise', () => {
    const described = tipFor('These fields have problems: hostgroup_name', true)
    expect(described).toContain('These fields have problems: hostgroup_name')
    expect(described).toContain('Setup')
    expect(described).toContain('host group')
  })

  it('leaves a rejection that is about something else alone', () => {
    expect(tipFor('Gateway timeout', true)).toBe('Gateway timeout')
  })

  it('leaves a single object alone, where there is no group to explain', () => {
    expect(tipFor('These fields have problems: hostgroup_name', false)).toBe(
      'These fields have problems: hostgroup_name'
    )
  })
})
