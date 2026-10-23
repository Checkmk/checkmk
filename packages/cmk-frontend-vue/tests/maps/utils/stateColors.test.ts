/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { onStateColorVar, stateColorVar } from '@/maps/utils/stateColors'

describe('stateColorVar', () => {
  it('names the shared state token of host and service states', () => {
    expect(stateColorVar('UP')).toBe('var(--color-state-up)')
    expect(stateColorVar('DOWN')).toBe('var(--color-state-down)')
    expect(stateColorVar('UNREACHABLE')).toBe('var(--color-state-unreachable)')
    expect(stateColorVar('OK')).toBe('var(--color-state-ok)')
    expect(stateColorVar('WARNING')).toBe('var(--color-state-warning)')
    expect(stateColorVar('CRITICAL')).toBe('var(--color-state-critical)')
    expect(stateColorVar('UNKNOWN')).toBe('var(--color-state-unknown)')
  })

  it('shows a missing, unknown or not found state as pending', () => {
    expect(stateColorVar(undefined)).toBe('var(--color-state-pending)')
    expect(stateColorVar('SOME_UNKNOWN_STATE')).toBe('var(--color-state-pending)')
    expect(stateColorVar('NOT_FOUND')).toBe('var(--color-state-pending)')
  })
})

describe('onStateColorVar', () => {
  it('writes on a state colour as the Checkmk themes do: black on warning, white otherwise', () => {
    expect(onStateColorVar('WARNING')).toBe('var(--black)')
    expect(onStateColorVar('UNKNOWN')).toBe('var(--white)')
    expect(onStateColorVar('CRITICAL')).toBe('var(--white)')
    expect(onStateColorVar('DOWN')).toBe('var(--white)')
  })

  it('leaves text on a state that is never filled solid to the theme', () => {
    expect(onStateColorVar('OK')).toBe('var(--font-color)')
    expect(onStateColorVar(undefined)).toBe('var(--font-color)')
  })
})
