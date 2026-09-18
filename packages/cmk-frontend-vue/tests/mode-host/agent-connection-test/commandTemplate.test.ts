/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type HostMacros,
  applyToken,
  requiresToken,
  substituteMacros
} from '@/mode-host/agent-connection-test/lib/commandTemplate'

const macros: HostMacros = {
  hostName: 'test-host',
  siteId: 'test-site',
  downloadServer: 'https://monitoring.example.test',
  registrationServer: 'monitoring.example.test:8000'
}

describe('substituteMacros', () => {
  test('resolves every macro of a download command', () => {
    expect(substituteMacros('get {{SERVER}}/{{SITE}} for {{HOSTNAME}}', 'download', macros)).toBe(
      'get https://monitoring.example.test/test-site for test-host'
    )
  })

  test('resolves {{SERVER}} to the agent receiver address for registration', () => {
    expect(substituteMacros('register --server {{SERVER}}', 'registration', macros)).toBe(
      'register --server monitoring.example.test:8000'
    )
  })

  test('resolves repeated occurrences of the same macro', () => {
    expect(substituteMacros('{{SITE}} {{SITE}}', 'download', macros)).toBe('test-site test-site')
  })

  test('returns an empty string for a missing command', () => {
    expect(substituteMacros(undefined, 'download', macros)).toBe('')
  })
})

describe('requiresToken', () => {
  test.each([
    ['install --auth 0:[AGENT_DOWNLOAD_OTT]', 'download' as const, true],
    ['install without a token', 'download' as const, false],
    ['register --user agent_registration', 'registration' as const, true],
    ['register --ott 0:already-set', 'registration' as const, false],
    // The placeholder and the flag are scope specific: neither counts for the
    // other scope, so a command cannot accidentally demand the wrong token.
    ['register --user agent_registration', 'download' as const, false],
    ['install --auth 0:[AGENT_DOWNLOAD_OTT]', 'registration' as const, false]
  ])('%s in scope %s requires a token: %s', (cmd, scope, expected) => {
    expect(requiresToken(cmd, scope)).toBe(expected)
  })

  test('a missing command requires no token', () => {
    expect(requiresToken(undefined, 'download')).toBe(false)
  })
})

describe('applyToken', () => {
  test('substitutes the download placeholder', () => {
    expect(applyToken('install --auth 0:[AGENT_DOWNLOAD_OTT]', 'download', 'tok')).toBe(
      'install --auth 0:tok'
    )
  })

  test('replaces the registration user flag with the token', () => {
    expect(applyToken('register --user agent_registration', 'registration', 'tok')).toBe(
      'register --ott 0:tok'
    )
  })

  test('substitutes every occurrence of the download placeholder', () => {
    expect(
      applyToken(
        'get 0:[AGENT_DOWNLOAD_OTT] && get-again 0:[AGENT_DOWNLOAD_OTT]',
        'download',
        'tok'
      )
    ).toBe('get 0:tok && get-again 0:tok')
  })

  test('substitutes every occurrence of the registration user flag', () => {
    expect(
      applyToken(
        'a --user agent_registration && b --user agent_registration',
        'registration',
        'tok'
      )
    ).toBe('a --ott 0:tok && b --ott 0:tok')
  })

  test('leaves a command that needs no token alone', () => {
    expect(applyToken('cmk-agent-ctl status', 'download', null)).toBe('cmk-agent-ctl status')
  })

  test.each([
    ['no token was generated', null],
    ['generation failed', new Error('nope')],
    ['the token is empty', '']
  ])('keeps the placeholder when %s', (_reason, token) => {
    expect(applyToken('install 0:[AGENT_DOWNLOAD_OTT]', 'download', token)).toBe(
      'install 0:[AGENT_DOWNLOAD_OTT]'
    )
  })

  test('returns an empty string for a missing command', () => {
    expect(applyToken(undefined, 'download', 'tok')).toBe('')
  })
})
