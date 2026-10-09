/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type RenderResult, render } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { afterEach, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { type ComponentProps } from 'vue-component-type-helpers'

import { FakeResizeObserver, deliverSize } from '@tests/lib/fakeResizeObserver'

export interface ComputeWidgetEndpoint<T> {
  requests: unknown[]
  answer(value: T): void
}

/** Serves one widget compute endpoint and records the bodies it receives. */
export function useComputeWidgetEndpoint<T>(
  action: string,
  value: () => T
): ComputeWidgetEndpoint<T> {
  const requests: unknown[] = []
  let current = value

  useMswServer(
    http.post(
      `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions/${action}/invoke`,
      async ({ request }) => {
        requests.push(await request.json())
        return HttpResponse.json({ domainType: 'widget-compute', value: current() })
      }
    )
  )

  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', FakeResizeObserver)
  })
  afterEach(() => {
    current = value
    requests.length = 0
    FakeResizeObserver.instances = []
    vi.unstubAllGlobals()
  })

  return {
    requests,
    answer: (next) => {
      current = () => next
    }
  }
}

/** Renders a computed widget and gives its figure frame a measured size. */
export async function renderComputedWidget<C>(
  component: C,
  props: ComponentProps<C>
): Promise<RenderResult> {
  const rendered = render(component, { props })
  await nextTick()
  deliverSize(400, 200)
  return rendered
}
