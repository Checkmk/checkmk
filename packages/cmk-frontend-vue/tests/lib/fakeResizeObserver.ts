/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/** A ResizeObserver for jsdom, which has none and does no layout. */
export class FakeResizeObserver {
  static instances: FakeResizeObserver[] = []
  readonly observed = new Set<Element>()

  constructor(public callback: ResizeObserverCallback) {
    FakeResizeObserver.instances.push(this)
  }

  observe(element: Element): void {
    this.observed.add(element)
  }

  unobserve(element: Element): void {
    this.observed.delete(element)
  }

  disconnect(): void {
    this.observed.clear()
  }

  fire(entries: ResizeObserverEntry[] = []): void {
    this.callback(entries, this as unknown as ResizeObserver)
  }
}

/** Report one content box size for every element that any fake observer observes. */
export function deliverSize(width: number, height: number): void {
  for (const observer of FakeResizeObserver.instances) {
    observer.fire(
      [...observer.observed].map(
        (target) =>
          ({
            target,
            contentBoxSize: [{ inlineSize: width, blockSize: height }],
            borderBoxSize: [{ inlineSize: width, blockSize: height }],
            devicePixelContentBoxSize: [],
            contentRect: { width, height }
          }) as unknown as ResizeObserverEntry
      )
    )
  }
}
