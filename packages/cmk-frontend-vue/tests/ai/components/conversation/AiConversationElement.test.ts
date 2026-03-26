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

function renderAiConversationElement(props: IAiConversationElement) {
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
        MarkdownContent: true,
        AlertContent: true,
        CodeContent: true,
        ListContent: true,
        DialogContent: true,
        ImageContent: true
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
