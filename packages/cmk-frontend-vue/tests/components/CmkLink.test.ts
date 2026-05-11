/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import CmkLink from '@/components/CmkLink.vue'

test('renders an anchor with the given href', () => {
  render(CmkLink, { props: { href: 'https://checkmk.com' } })
  const link = screen.getByRole('link')
  expect(link).toHaveAttribute('href', 'https://checkmk.com')
})

test('renders slot content', () => {
  const testComponent = defineComponent({
    components: { CmkLink },
    template: `<CmkLink href="/foo">Click me</CmkLink>`
  })
  render(testComponent)
  expect(screen.getByRole('link')).toHaveTextContent('Click me')
})

test('does not set target attribute when not provided', () => {
  render(CmkLink, { props: { href: '/foo' } })
  const link = screen.getByRole('link')
  expect(link).not.toHaveAttribute('target')
})

test('sets target attribute when provided', () => {
  render(CmkLink, { props: { href: '/foo', target: '_blank' } })
  const link = screen.getByRole('link')
  expect(link).toHaveAttribute('target', '_blank')
})

test('has cmk-link class', () => {
  render(CmkLink, { props: { href: '/foo' } })
  expect(screen.getByRole('link')).toHaveClass('cmk-link')
})

test('exposes focus method that focuses the anchor', async () => {
  const componentRef = ref<InstanceType<typeof CmkLink> | null>(null)
  const testComponent = defineComponent({
    components: { CmkLink },
    setup() {
      return { componentRef }
    },
    template: `<CmkLink ref="componentRef" href="/foo">Focus me</CmkLink>`
  })
  render(testComponent)
  const link = screen.getByRole('link')
  link.focus = vi.fn()
  componentRef.value?.focus()
  expect(link.focus).toHaveBeenCalled()
})
