/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { Api } from 'cmk-ui-library/lib/api-client'

import GenerateToken from '@/mode-host/agent-connection-test/components/GenerateToken.vue'

function mockSuccessfulTokenGeneration(expiresInSeconds: number) {
  vi.spyOn(Api.prototype, 'post').mockResolvedValue({
    id: 'test-token-123',
    title: 'Test Token',
    domainType: 'registration_token',
    extensions: {
      comment: '',
      issued_at: new Date(),
      expires_at: new Date(Date.now() + expiresInSeconds * 1000),
      host_name: 'test-host'
    }
  })
}

describe('GenerateToken', () => {
  afterEach(() => {
    cleanup()
  })

  test.each([
    [30, /This token remains valid for 30 seconds\./],
    [60, /This token remains valid for 1 minute\./],
    [90, /This token remains valid for 2 minutes\./],
    [3600, /This token remains valid for 1 hour\./],
    [7200, /This token remains valid for 2 hours\./],
    [86400, /This token remains valid for 1 day\./],
    [172800, /This token remains valid for 2 days\./]
  ])('shows validity text for %ds', async (seconds, expectedPattern) => {
    mockSuccessfulTokenGeneration(seconds)

    render(GenerateToken, {
      props: {
        tokenGenerationEndpointUri: 'domain-types/token/collections/all',
        tokenGenerationBody: {},
        expiresInSeconds: seconds,
        showValidityText: true,
        modelValue: null
      },
      global: { stubs: { teleport: true } }
    })

    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(expectedPattern)
  })

  test('falls back to expiry timestamp when no expiresInSeconds', async () => {
    mockSuccessfulTokenGeneration(3600)

    render(GenerateToken, {
      props: {
        tokenGenerationEndpointUri: 'domain-types/token/collections/all',
        tokenGenerationBody: {},
        modelValue: null
      },
      global: { stubs: { teleport: true } }
    })

    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(/Successfully generated one-time token/)
  })

  test('falls back to expiry timestamp when expiresInSeconds set but showValidityText absent', async () => {
    mockSuccessfulTokenGeneration(3600)

    render(GenerateToken, {
      props: {
        tokenGenerationEndpointUri: 'domain-types/token/collections/all',
        tokenGenerationBody: {},
        expiresInSeconds: 3600,
        modelValue: null
      },
      global: { stubs: { teleport: true } }
    })

    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(/Successfully generated one-time token/)
  })

  test('replaces the token with a newly generated one', async () => {
    const post = vi
      .spyOn(Api.prototype, 'post')
      .mockResolvedValueOnce({ id: 'first-token', extensions: { expires_at: null } })
      .mockResolvedValueOnce({ id: 'second-token', extensions: { expires_at: null } })

    const { emitted } = render(GenerateToken, {
      props: {
        tokenGenerationEndpointUri: 'domain-types/token/collections/all',
        tokenGenerationBody: {},
        modelValue: null
      },
      global: { stubs: { teleport: true } }
    })

    await userEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await userEvent.click(await screen.findByRole('button', { name: /generate new token/i }))

    await vi.waitFor(() => expect(post).toHaveBeenCalledTimes(2))
    expect(emitted('update:modelValue')).toEqual([['first-token'], ['second-token']])
  })

  test('sends the expiry again when the parent passes a new body object', async () => {
    const post = vi
      .spyOn(Api.prototype, 'post')
      .mockResolvedValue({ id: 'token', extensions: { expires_at: null } })

    const { rerender } = render(GenerateToken, {
      props: {
        tokenGenerationEndpointUri: 'domain-types/token/collections/all',
        tokenGenerationBody: { site_id: 'heute' },
        expiresInSeconds: 3600,
        modelValue: null
      },
      global: { stubs: { teleport: true } }
    })

    await userEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await rerender({ tokenGenerationBody: { site_id: 'heute' }, modelValue: 'token' })
    await userEvent.click(await screen.findByRole('button', { name: /generate new token/i }))

    await vi.waitFor(() => expect(post).toHaveBeenCalledTimes(2))
    expect(post.mock.calls[1]![1]).toEqual({ site_id: 'heute', expires_at: expect.any(Date) })
  })

  test('keeps the previous token when generating a new one fails', async () => {
    vi.spyOn(Api.prototype, 'post')
      .mockResolvedValueOnce({ id: 'first-token', extensions: { expires_at: null } })
      .mockRejectedValueOnce(new Error('boom'))

    const { emitted, rerender } = render(GenerateToken, {
      props: {
        tokenGenerationEndpointUri: 'domain-types/token/collections/all',
        tokenGenerationBody: {},
        modelValue: null
      },
      global: { stubs: { teleport: true } }
    })

    await userEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await rerender({ modelValue: 'first-token' })
    await userEvent.click(await screen.findByRole('button', { name: /generate new token/i }))

    await screen.findByText(/Error generating one-time token: boom/)
    screen.getByText(/Successfully generated one-time token/)
    expect(emitted('update:modelValue')).toEqual([['first-token']])
  })
})
