/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  GlobalSettingsTopic,
  GlobalSettingsVariable
} from 'cmk-shared-typing/typescript/global_settings'
import { describe, expect, test } from 'vitest'

import { buildSearchIndex, matchTopics } from '@/global-settings/lib/search'

function variable(name: string, title: string, help: string = ''): GlobalSettingsVariable {
  return {
    name,
    spec: {
      type: 'integer',
      title,
      help,
      validators: [],
      label: null,
      unit: null,
      input_hint: null
    },
    value: 10,
    default_value: 10,
    modified: false,
    site_overrides: []
  }
}

function topic(
  headline: string,
  subline: string,
  variables: GlobalSettingsVariable[]
): GlobalSettingsTopic {
  return { icon: 'users', headline, subline, warning: null, variables }
}

const topics: GlobalSettingsTopic[] = [
  topic('User management', 'Configures user/authentication settings', [
    variable('lock_on_logon_failures', 'Lock user accounts after N login failures'),
    variable('user_idle_timeout', 'Login session idle timeout', 'Helpful help text')
  ]),
  topic('Site management', 'Configures site settings', [variable('site_setting', 'Site setting')])
]

function match(query: string): ReturnType<typeof matchTopics> {
  return matchTopics(buildSearchIndex(topics), query)
}

describe('matchTopics', () => {
  test('an empty query means no active search', () => {
    expect(match('')).toBeNull()
  })

  test('a whitespace-only query means no active search', () => {
    expect(match('   ')).toBeNull()
  })

  test('the query is trimmed and matched case-insensitively', () => {
    expect(match('  SITE SETTING  ')).toEqual(
      new Map([['Site management', new Set(['site_setting'])]])
    )
  })

  test('only a contiguous substring matches', () => {
    expect(match('login failures')?.get('User management')).toEqual(
      new Set(['lock_on_logon_failures'])
    )
    expect(match('login accounts')?.has('User management')).toBe(false)
  })

  test('the topic headline is not searched', () => {
    expect(match('user management')).toEqual(new Map())
  })

  test('the topic subline is not searched', () => {
    expect(match('user/authentication')).toEqual(new Map())
  })

  test('a variable title hit yields only that variable', () => {
    expect(match('idle timeout')?.get('User management')).toEqual(new Set(['user_idle_timeout']))
  })

  test('a variable name hit yields only that variable', () => {
    expect(match('lock_on_logon')?.get('User management')).toEqual(
      new Set(['lock_on_logon_failures'])
    )
  })

  test('the help text is not searched', () => {
    expect(match('Helpful help text')).toEqual(new Map())
  })

  test('a topic without any hit is absent from the result', () => {
    expect(match('idle timeout')?.has('Site management')).toBe(false)
  })

  test('the query cannot match across field boundaries', () => {
    expect(match('lock_on_logon_failures lock')).toEqual(new Map())
  })

  test('the input topics are not mutated', () => {
    const before = structuredClone(topics)
    match('site setting')
    expect(topics).toEqual(before)
  })
})
