/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkHtml from 'cmk-ui-library/components/CmkHtml.vue'
import {
  ACTIVE_MARKUP,
  BOUNDARY_MARKUP,
  type SurfacePolicy,
  activeContentIn
} from 'cmk-ui-library/vitest.sanitize'
import { defineComponent } from 'vue'

test.each([
  ['<h1>abc</h1>', null],
  ['<h2>abc</h2>', null],
  ['<b>abc</b>', null],
  ['<tt>abc</tt>', null],
  ['<i>abc</i>', null],
  ['<u>abc</u>', null],
  ['<br>', null],
  ['<nobr></nobr>', null],
  ['<pre></pre>', null],
  ['<sup></sup>', null],
  ['<p></p>', null],
  ['<li></li>', null],
  ['<ul></ul>', null],
  ['<ol></ol>', null],
  ["<a href='xyz'>abc</a>", null],
  ["<a href='xyz' target='123'>abc</a>", null],
  ["blah<a href='link0'>aaa</a>blah<a href='link1' target='ttt'>bbb</a>", null],
  ["'I am not a link' target='still not a link'", "'I am not a link' target='still not a link'"],
  // The next test is perverse: it contains the string `target=` inside of an
  // <a> tag (which must be unescaped) as well as outside (which must not).
  [
    "<a href='aaa'>bbb</a>not a link target='really'<a href='ccc' target='ttt'>ddd</a>",
    "<a href='aaa'>bbb</a>not a link target='really'<a href='ccc' target='ttt'>ddd</a>"
  ],
  [
    "<a href='xyz'>abc</a><script>alert(1)</script><a href='xyz'>abc</a>",
    "<a href='xyz'>abc</a><a href='xyz'>abc</a>"
  ],
  ['&nbsp;', null],
  // Only http/https/mailto are allowed as schemes
  ["<a href='http://checkmk.com/'>abc</a>", null],
  ["<a href='https://checkmk.com/'>abc</a>", null],
  ["<a href='HTTP://CHECKMK.COM/'>abc</a>", null],
  [
    "Please download it manually and send it to <a href='mailto:feedback@checkmk.com?subject=Checkmk+Crash+Report+-+2021.11.12'>feedback@checkmk.com</a>",
    "Please download it manually and send it to <a href='mailto:feedback@checkmk.com?subject=Checkmk+Crash+Report+-+2021.11.12'>feedback@checkmk.com</a>"
  ]
])('Escapes text correctly: %s', (input: string, expected: string | null) => {
  const testComponent = defineComponent({
    components: { CmkHtml },
    props: {
      html: String
    },
    setup(props) {
      return { props }
    },
    template: `
      <div data-testid="html">
        <CmkHtml :html="props.html" />
      </div>
    `
  })

  render(testComponent, {
    props: {
      html: input
    }
  })

  const component = screen.getByTestId<HTMLElement>('html')
  if (expected === null) {
    expect(component).toContainHTML(input)
  } else {
    expect(component).toContainHTML(expected)
  }
})

const MESSAGE: SurfacePolicy = {
  tags: [
    'h1',
    'h2',
    'b',
    'tt',
    'i',
    'u',
    'hr',
    'br',
    'nobr',
    'pre',
    'sup',
    'p',
    'li',
    'ul',
    'ol',
    'a'
  ],
  attributes: ['href', 'name', 'target'],
  classes: [],
  protocols: ['http:', 'https:', 'mailto:'],
  namedTargets: true
}

function renderedMessage(html: string): HTMLSpanElement {
  const { container } = render(CmkHtml, { props: { html } })
  const [wrapper, ...others] = container.children
  if (!(wrapper instanceof HTMLSpanElement) || others.length > 0) {
    throw new Error(`CmkHtml rendered ${container.innerHTML} instead of one span`)
  }
  return wrapper
}

test.each(ACTIVE_MARKUP)('renders %s as inert', (markup) => {
  const message = renderedMessage(markup)

  expect(activeContentIn(message, MESSAGE)).toEqual([])
})

test.each(BOUNDARY_MARKUP)('keeps %s within the message policy, showing %s', (markup, text) => {
  const message = renderedMessage(markup)

  expect(activeContentIn(message, MESSAGE)).toEqual([])
  expect(message.textContent).toBe(text)
})
