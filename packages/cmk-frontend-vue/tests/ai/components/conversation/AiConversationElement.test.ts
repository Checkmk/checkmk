/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import AiConversationElement from '@/ai/components/conversation/AiConversationElement.vue'
import { aiTemplateKey } from '@/ai/lib/provider/ai-template'
import type { IAiConversationElement } from '@/ai/lib/service/ai-template'
import { AiRole } from '@/ai/lib/utils'

const mockAiTemplate = {
  setAnimationActiveChange: vi.fn(),
  markElementDisplayed: vi.fn(),
  setActiveRole: vi.fn()
}

const copyProxyStub = defineComponent({
  props: {
    text: {
      type: String,
      required: true
    }
  },
  template: '<div data-testid="copy-proxy" :data-text="text"><slot /></div>'
})

function renderAiConversationElement(props: IAiConversationElement): ReturnType<typeof render> {
  return render(AiConversationElement, {
    props,
    global: {
      provide: {
        [aiTemplateKey as symbol]: ref(mockAiTemplate)
      },
      stubs: {
        CmkCopy: copyProxyStub,
        CmkIcon: true,
        CmkHeading: true,
        CmkIconButton: {
          props: ['title'],
          template: '<button type="button" :title="title"><slot /></button>'
        },
        MarkdownContent: {
          props: ['content', 'title', 'noAnimation', 'streaming'],
          template:
            '<div data-testid="markdown-content-stub" :data-content="content" :data-title="title"></div>'
        },
        CmkTooltipProvider: { template: '<div><slot /></div>' },
        CmkTooltip: { template: '<div><slot /></div>' },
        CmkTooltipTrigger: { template: '<div><slot /></div>' },
        CmkTooltipContent: { template: '<div><slot /></div>' },
        AlertContent: true,
        CodeContent: true,
        ListContent: true,
        DialogContent: true,
        ImageContent: true,
        RateLimitContent: {
          template: '<div data-testid="ai-rate-limit-content"></div>'
        }
      }
    }
  })
}

afterEach(() => {
  vi.clearAllMocks()
})

test('shows copy button after answer is complete', async () => {
  renderAiConversationElement({
    role: AiRole.ai,
    streaming: false,
    noAnimation: true,
    content: [
      { content_type: 'markdown', content: 'thinking', title: 'thinking' },
      { content_type: 'markdown', content: 'final answer', title: 'answer' }
    ]
  })

  await waitFor(() => {
    expect(screen.getByTitle('Copy answer')).toBeInTheDocument()
  })
})

test('does not show copy button while still thinking', () => {
  renderAiConversationElement({
    role: AiRole.ai,
    streaming: true,
    noAnimation: true,
    content: [{ content_type: 'markdown', content: 'still thinking', title: 'thinking' }]
  })

  expect(screen.queryByTitle('Copy answer')).not.toBeInTheDocument()
})

test('renders RateLimitContent when content_type is rate_limit', async () => {
  renderAiConversationElement({
    role: AiRole.ai,
    streaming: false,
    noAnimation: true,
    content: [{ content_type: 'rate_limit' }]
  })

  await waitFor(() => {
    expect(screen.getByTestId('ai-rate-limit-content')).toBeInTheDocument()
  })
})

test.each([
  ['canonical High', 'Data Quality: **High**', 'high'],
  ['lowercase label and level', 'data quality: **low**', 'low'],
  ['legacy Confidence Medium', 'Confidence: **Medium**', 'medium']
])('shows the parsed badge level for %s', async (_desc, qualityLine, level) => {
  renderAiConversationElement({
    role: AiRole.ai,
    streaming: false,
    noAnimation: true,
    content: [{ content_type: 'markdown', content: `Answer\n\n${qualityLine}`, title: 'answer' }]
  })

  await waitFor(() => {
    const levelWord = ({ high: 'High', medium: 'Medium', low: 'Low' } as const)[
      level as 'high' | 'medium' | 'low'
    ]
    expect(screen.getByRole('img', { name: `Data quality: ${levelWord}` })).toBeInTheDocument()
  })
})

test.each([
  [
    'answer is complete but has no quality line',
    {
      streaming: false,
      content: [
        { content_type: 'markdown', content: 'Answer without a quality line', title: 'answer' }
      ]
    }
  ],
  [
    'the only quality line lives in a thinking chunk',
    {
      streaming: false,
      content: [
        { content_type: 'markdown', content: 'Data Quality: **High**', title: 'thinking' },
        { content_type: 'markdown', content: 'Answer without a quality line', title: 'answer' }
      ]
    }
  ],
  [
    'response is a rate-limit (no answer chunk, no fallback)',
    { streaming: false, content: [{ content_type: 'rate_limit' }] }
  ],
  [
    'still streaming a thinking chunk',
    {
      streaming: true,
      content: [{ content_type: 'markdown', content: 'still thinking', title: 'thinking' }]
    }
  ],
  [
    'streaming an answer that has no quality line yet',
    {
      streaming: true,
      content: [
        { content_type: 'markdown', content: 'Answer so far, no line yet', title: 'answer' }
      ]
    }
  ]
] as const)('keeps the badge hidden (never low) when %s', async (_desc, { streaming, content }) => {
  renderAiConversationElement({
    role: AiRole.ai,
    streaming,
    noAnimation: true,
    content: content as unknown as IAiConversationElement['content']
  })

  await waitFor(() => {
    expect(screen.queryByRole('img', { name: /Data quality/ })).not.toBeInTheDocument()
  })
})

test('quality line is stripped from both screen and copy', async () => {
  renderAiConversationElement({
    role: AiRole.ai,
    streaming: false,
    noAnimation: true,
    content: [
      {
        content_type: 'markdown',
        content: 'Answer text\n\nData Quality: **High**',
        title: 'answer'
      }
    ]
  })

  await waitFor(() => {
    const stub = screen.getByTestId('markdown-content-stub')
    expect(stub.getAttribute('data-content')).toContain('Answer text')
    expect(stub.getAttribute('data-content')).not.toContain('Data Quality:')
    const dataText = screen.getByTestId('copy-proxy').getAttribute('data-text')
    expect(dataText).toContain('Answer text')
    expect(dataText).not.toContain('Data Quality:')
  })
})

test('builds copy text from answer chunks and excludes thinking', async () => {
  renderAiConversationElement({
    role: AiRole.ai,
    streaming: false,
    noAnimation: true,
    content: [
      { content_type: 'markdown', content: 'thoughts', title: 'thinking' },
      { content_type: 'markdown', content: 'Answer part 1', title: 'answer' },
      { content_type: 'text', text: 'plain text chunk' },
      { content_type: 'list', listType: 'unordered', items: ['item a', 'item b'] },
      { content_type: 'code', code: 'echo test' }
    ]
  })

  await waitFor(() => {
    expect(screen.getByTestId('copy-proxy')).toHaveAttribute(
      'data-text',
      'Answer part 1\n\nplain text chunk\n\nitem a\nitem b\n\necho test'
    )
  })
})
