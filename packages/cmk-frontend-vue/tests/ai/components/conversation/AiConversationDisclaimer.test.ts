/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { ref } from 'vue'

import AiConversationDisclaimer from '@/ai/components/conversation/AiConversationDisclaimer.vue'
import type { InfoResponse } from '@/ai/lib/ai-api-client'
import { aiTemplateKey } from '@/ai/lib/provider/ai-template'

function makeTemplate(
  overrides: {
    isDisclaimerShown?: () => boolean
    persistDisclaimerShown?: ReturnType<typeof vi.fn>
    info?: InfoResponse | null
    onInfoLoaded?: (cb: () => void) => void
  } = {}
) {
  return {
    isDisclaimerShown: vi.fn().mockReturnValue(false),
    persistDisclaimerShown: vi.fn(),
    onInfoLoaded: vi.fn(),
    info: null,
    ...overrides
  }
}

function renderDisclaimer(template = makeTemplate()) {
  return render(AiConversationDisclaimer, {
    global: {
      provide: {
        [aiTemplateKey as symbol]: ref(template)
      },
      stubs: {
        CmkHeading: {
          template: '<div data-testid="heading"><slot /></div>'
        },
        CmkSkeleton: {
          template: '<div data-testid="skeleton" />'
        },
        CmkButton: {
          props: ['variant', 'disabled'],
          template:
            '<button type="button" :data-variant="variant" :disabled="disabled"><slot /></button>'
        }
      }
    }
  })
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('AiConversationDisclaimer — visibility', () => {
  test('shows the disclaimer when consent has not been given yet', async () => {
    renderDisclaimer(makeTemplate({ isDisclaimerShown: () => false }))

    await waitFor(() => {
      expect(screen.getByTestId('heading')).toBeInTheDocument()
      expect(screen.getByText('Checkmk AI feature usage notice')).toBeInTheDocument()
    })
  })

  test('shows a skeleton instead when the disclaimer has already been acknowledged', async () => {
    renderDisclaimer(makeTemplate({ isDisclaimerShown: () => true }))

    await waitFor(() => {
      expect(screen.getByTestId('skeleton')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('heading')).not.toBeInTheDocument()
  })
})

describe('AiConversationDisclaimer — consent flow', () => {
  test('clicking "Start AI feature" calls persistDisclaimerShown', async () => {
    const persistDisclaimerShown = vi.fn()
    renderDisclaimer(makeTemplate({ persistDisclaimerShown }))

    await waitFor(() => {
      expect(screen.getByText('Start AI feature')).toBeInTheDocument()
    })

    await fireEvent.click(screen.getByText('Start AI feature'))

    expect(persistDisclaimerShown).toHaveBeenCalledOnce()
  })

  test('clicking "Start AI feature" emits the consent event', async () => {
    const { emitted } = renderDisclaimer()

    await waitFor(() => {
      expect(screen.getByText('Start AI feature')).toBeInTheDocument()
    })

    await fireEvent.click(screen.getByText('Start AI feature'))

    expect(emitted('consent')).toHaveLength(1)
  })

  test('clicking "Cancel and go back" emits the decline event', async () => {
    const { emitted } = renderDisclaimer()

    await waitFor(() => {
      expect(screen.getByText('Cancel and go back')).toBeInTheDocument()
    })

    await fireEvent.click(screen.getByText('Cancel and go back'))

    expect(emitted('decline')).toHaveLength(1)
  })

  test('hides the action buttons after consent is given', async () => {
    renderDisclaimer()

    await waitFor(() => {
      expect(screen.getByText('Start AI feature')).toBeInTheDocument()
    })

    await fireEvent.click(screen.getByText('Start AI feature'))

    await waitFor(() => {
      expect(screen.queryByText('Start AI feature')).not.toBeInTheDocument()
      expect(screen.queryByText('Cancel and go back')).not.toBeInTheDocument()
    })
  })
})

describe('AiConversationDisclaimer — AI info interpolation', () => {
  test('interpolates model and provider names into the body when info is already available', async () => {
    const info: InfoResponse = {
      service_name: 'test',
      version: '1',
      models: ['GPT-4'],
      provider: 'OpenAI'
    }
    renderDisclaimer(makeTemplate({ info }))

    // The interpolated text sits inside a div that also contains link text, so
    // we verify the body contains the interpolated string rather than exact-matching
    // a single element.
    await waitFor(() => {
      expect(document.body.textContent).toContain('[GPT-4] of [OpenAI]')
    })
  })

  test('updates the body text once info loads via onInfoLoaded callback', async () => {
    let infoCallback: (() => void) | undefined
    const template = makeTemplate({
      onInfoLoaded: (cb) => {
        infoCallback = cb
      },
      info: null
    })

    renderDisclaimer(template)

    await waitFor(() => {
      expect(screen.getByTestId('heading')).toBeInTheDocument()
    })

    // Simulate info becoming available after mount
    template.info = {
      service_name: 'test',
      version: '1',
      models: ['Claude'],
      provider: 'Anthropic'
    } as InfoResponse
    infoCallback!()

    await waitFor(() => {
      expect(document.body.textContent).toContain('[Claude] of [Anthropic]')
    })
  })

  test('handles multiple models by joining them with a comma', async () => {
    const info: InfoResponse = {
      service_name: 'test',
      version: '1',
      models: ['GPT-4', 'GPT-3.5'],
      provider: 'OpenAI'
    }
    renderDisclaimer(makeTemplate({ info }))

    await waitFor(() => {
      expect(document.body.textContent).toContain('[GPT-4, GPT-3.5] of [OpenAI]')
    })
  })
})
