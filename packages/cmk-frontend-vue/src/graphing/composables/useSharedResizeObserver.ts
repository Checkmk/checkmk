/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref } from 'vue'

import { sharedObserver, useObservedElement } from './sharedObserver'

const observeResize = sharedObserver<ResizeObserverEntry>(
  (callback) => new ResizeObserver(callback)
)

/** Run onResize when target resizes; all callers on the page share one ResizeObserver. */
export function useSharedResizeObserver(
  target: Readonly<Ref<Element | null>>,
  onResize: (entry: ResizeObserverEntry) => void
): void {
  if (typeof ResizeObserver === 'undefined') {
    return
  }
  useObservedElement(observeResize, target, onResize)
}
