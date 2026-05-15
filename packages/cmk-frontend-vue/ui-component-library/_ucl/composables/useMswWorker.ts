/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { RequestHandler } from 'msw'
import type { StartOptions } from 'msw/browser'
import { setupWorker } from 'msw/browser'
import { onBeforeMount, onBeforeUnmount, ref } from 'vue'

export function useMswWorker(
  handlers: RequestHandler[],
  options: Omit<StartOptions, 'serviceWorker'> & { afterStart?: () => Promise<void> } = {}
) {
  const { afterStart, ...startOptions } = options
  const mockLoaded = ref(false)
  const worker = setupWorker(...handlers)

  onBeforeMount(async () => {
    await worker.start({
      ...startOptions,
      serviceWorker: { url: `${import.meta.env.BASE_URL}mockServiceWorker.js` }
    })
    await afterStart?.()
    mockLoaded.value = true
  })

  onBeforeUnmount(() => worker.stop())

  return { mockLoaded }
}
