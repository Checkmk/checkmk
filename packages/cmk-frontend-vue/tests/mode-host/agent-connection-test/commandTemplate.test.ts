/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type HostMacros,
  applyToken,
  isResolved,
  requiresToken,
  substituteMacros
} from '@/mode-host/agent-connection-test/lib/commandTemplate'

import { commandPlaceholders } from './fixtures'

const macros: HostMacros = {
  hostName: 'test-host',
  siteId: 'test-site',
  downloadServer: 'https://monitoring.example.test',
  registrationServer: 'monitoring.example.test:8000',
  placeholders: commandPlaceholders
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

describe('the placeholders the page hands over', () => {
  const renamed = {
    ...commandPlaceholders,
    host_name: '<<HOST>>',
    download_token: '<<DOWNLOAD_TOKEN>>'
  }

  test('decide what is substituted', () => {
    expect(
      substituteMacros('register <<HOST>> {{HOSTNAME}}', 'download', {
        ...macros,
        placeholders: renamed
      })
    ).toBe('register test-host {{HOSTNAME}}')
  })

  test('decide where a token goes', () => {
    expect(applyToken('install 0:<<DOWNLOAD_TOKEN>>', 'download', 'tok', renamed).text).toBe(
      'install 0:tok'
    )
  })
})

describe('requiresToken', () => {
  test.each([
    ['install --auth 0:[AGENT_DOWNLOAD_OTT]', 'download' as const, true],
    ['install without a token', 'download' as const, false],
    ['register --user agent_registration', 'registration' as const, true],
    ['register --ott 0:already-set', 'registration' as const, false],
    ['helm --set token=[AGENT_REGISTRATION_OTT]', 'registration' as const, true],
    // The placeholder and the flag are scope specific: neither counts for the
    // other scope, so a command cannot accidentally demand the wrong token.
    ['register --user agent_registration', 'download' as const, false],
    ['install --auth 0:[AGENT_DOWNLOAD_OTT]', 'registration' as const, false],
    ['helm --set token=[AGENT_REGISTRATION_OTT]', 'download' as const, false]
  ])('%s in scope %s requires a token: %s', (cmd, scope, expected) => {
    expect(requiresToken(cmd, scope, commandPlaceholders)).toBe(expected)
  })

  test('a missing command requires no token', () => {
    expect(requiresToken(undefined, 'download', commandPlaceholders)).toBe(false)
  })
})

describe('applyToken', () => {
  test('substitutes the download placeholder', () => {
    expect(
      applyToken('install --auth 0:[AGENT_DOWNLOAD_OTT]', 'download', 'tok', commandPlaceholders)
    ).toEqual({
      text: 'install --auth 0:tok',
      tokenState: 'ready'
    })
  })

  test('replaces the registration user flag with the token', () => {
    expect(
      applyToken('register --user agent_registration', 'registration', 'tok', commandPlaceholders)
    ).toEqual({
      text: 'register --ott 0:tok',
      tokenState: 'ready'
    })
  })

  test('substitutes the registration token placeholder', () => {
    expect(
      applyToken(
        'helm --set token=[AGENT_REGISTRATION_OTT]',
        'registration',
        'tok',
        commandPlaceholders
      )
    ).toEqual({
      text: 'helm --set token=0:tok',
      tokenState: 'ready'
    })
  })

  test('substitutes every occurrence of the download placeholder', () => {
    expect(
      applyToken(
        'get 0:[AGENT_DOWNLOAD_OTT] && again 0:[AGENT_DOWNLOAD_OTT]',
        'download',
        'tok',
        commandPlaceholders
      ).text
    ).toBe('get 0:tok && again 0:tok')
  })

  test('substitutes every occurrence of the registration user flag', () => {
    expect(
      applyToken(
        'a --user agent_registration && b --user agent_registration',
        'registration',
        'tok',
        commandPlaceholders
      ).text
    ).toBe('a --ott 0:tok && b --ott 0:tok')
  })

  test('reports a command that needs no token as resolved', () => {
    const rendered = applyToken('cmk-agent-ctl status', 'download', null, commandPlaceholders)
    expect(rendered).toEqual({ text: 'cmk-agent-ctl status', tokenState: 'not-required' })
    expect(isResolved(rendered.tokenState)).toBe(true)
  })

  test.each([
    ['no token was generated', null, 'missing'],
    ['the token is empty', '', 'missing'],
    ['generation failed', new Error('nope'), 'failed']
  ])('keeps the placeholder when %s', (_reason, token, tokenState) => {
    const rendered = applyToken(
      'install 0:[AGENT_DOWNLOAD_OTT]',
      'download',
      token,
      commandPlaceholders
    )
    expect(rendered).toEqual({ text: 'install 0:[AGENT_DOWNLOAD_OTT]', tokenState })
    expect(isResolved(rendered.tokenState)).toBe(false)
  })

  test('returns an empty string for a missing command', () => {
    expect(applyToken(undefined, 'download', 'tok', commandPlaceholders)).toEqual({
      text: '',
      tokenState: 'not-required'
    })
  })
})
