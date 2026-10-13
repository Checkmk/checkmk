/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkNetworkError } from 'cmk-ui-library/lib/error'

/**
 * `fetch`, rejecting with a `CmkNetworkError` when the browser got no response.
 *
 * A request aborted through its own signal still rejects with the abort reason. `fetch` is looked
 * up per request, so a later replacement of the global is picked up.
 */
export async function networkAwareFetch(
  ...[input, init]: Parameters<typeof fetch>
): Promise<Response> {
  try {
    return await globalThis.fetch(input, init)
  } catch (e: unknown) {
    if (init?.signal?.aborted || (input instanceof Request && input.signal.aborted)) {
      throw e
    }
    throw new CmkNetworkError(e instanceof Error ? e : new Error(String(e)))
  }
}
