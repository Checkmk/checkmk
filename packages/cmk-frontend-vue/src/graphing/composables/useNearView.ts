/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref } from 'vue'

import { sharedObserver, useObservedElement } from './sharedObserver'

const observeNearView = sharedObserver<IntersectionObserverEntry>(
  (callback) =>
    new IntersectionObserver(
      callback,
      // One view height ahead of a scroll, so that a target does not come into view empty. The
      // scroll margin widens the scroll containers between target and viewport, e.g. the one of a
      // view in an iframe.
      { root: document, rootMargin: '100% 0px', scrollMargin: '100% 0px' }
    )
)

const canObserveNearView = (): boolean => typeof IntersectionObserver !== 'undefined'

/** Return a request that runs run at once near the view, else when target comes near it. */
export function useWhenNearView(
  target: Readonly<Ref<Element | null>>,
  run: () => void
): () => void {
  if (!canObserveNearView()) {
    return run
  }
  let isNear = false
  let requested = false
  useObservedElement(observeNearView, target, (entry) => {
    isNear = entry.isIntersecting
    if (isNear && requested) {
      requested = false
      run()
    }
  })

  return () => {
    if (isNear) {
      run()
    } else {
      requested = true
    }
  }
}
