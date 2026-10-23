/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  configNameFormatErrors,
  configNameTakenErrors,
  nextAvailableConfigName
} from '@/lib/configuration-name'

describe('nextAvailableConfigName', () => {
  test('returns the first slot for an empty list', () => {
    expect(nextAvailableConfigName([], 'opentelemetry_config_')).toBe('opentelemetry_config_1')
  })

  test('returns max(existing) + 1', () => {
    expect(
      nextAvailableConfigName(
        ['opentelemetry_config_1', 'opentelemetry_config_2'],
        'opentelemetry_config_'
      )
    ).toBe('opentelemetry_config_3')
  })

  test('skips gaps by using the highest index, not the count', () => {
    expect(
      nextAvailableConfigName(
        ['opentelemetry_config_1', 'opentelemetry_config_5'],
        'opentelemetry_config_'
      )
    ).toBe('opentelemetry_config_6')
  })

  test('ignores ids that do not match the prefix or are not numbered', () => {
    expect(
      nextAvailableConfigName(
        [
          'my_custom_name',
          'opentelemetry_config_',
          'opentelemetry_config_2',
          'prometheus_config_9'
        ],
        'opentelemetry_config_'
      )
    ).toBe('opentelemetry_config_3')
  })
})

describe('configNameFormatErrors', () => {
  test.each(['valid_name', '_leading_underscore', 'with-dash', 'a1'])('accepts %s', (name) => {
    expect(configNameFormatErrors(name)).toEqual([])
  })

  test.each(['', '   '])('requires a name (%j)', (name) => {
    expect(configNameFormatErrors(name)).toEqual([
      'Configuration name is required but not specified.'
    ])
  })

  test.each(['1starts_with_digit', 'has space', 'dot.ted', 'ümlaut'])('rejects %s', (name) => {
    expect(configNameFormatErrors(name)).toEqual([
      'The name must only consist of letters, digits, dash and underscore and it must start with a letter or underscore.'
    ])
  })
})

describe('configNameTakenErrors', () => {
  test('rejects a name already in use', () => {
    expect(configNameTakenErrors('taken', ['other', 'taken'])).toEqual([
      'A configuration with this name already exists. Choose a different name.'
    ])
  })

  test('accepts a free name', () => {
    expect(configNameTakenErrors('free', ['other', 'taken'])).toEqual([])
  })
})
