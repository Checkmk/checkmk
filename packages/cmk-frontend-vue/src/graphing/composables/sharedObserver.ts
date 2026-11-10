/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onScopeDispose, watch } from 'vue'

interface ElementObserver {
  observe: (target: Element) => void
  unobserve: (target: Element) => void
  disconnect: () => void
}

/** Tell listener each entry that the observer reports for target; return the stop. */
export type ObserveElement<Entry> = (
  target: Element,
  listener: (entry: Entry) => void
) => () => void

/** Observe all targets through one observer, so that the work for all of them runs in one callback. */
export function sharedObserver<Entry extends { target: Element }>(
  create: (callback: (entries: Entry[]) => void) => ElementObserver
): ObserveElement<Entry> {
  const listeners = new Map<Element, Set<(entry: Entry) => void>>()
  let observer: ElementObserver | null = null

  return (target, listener) => {
    observer ??= create((entries) =>
      entries.forEach((entry) => listeners.get(entry.target)?.forEach((each) => each(entry)))
    )
    // A wrapper of its own, so that two callers with the same listener stop independently.
    const registration = (entry: Entry): void => listener(entry)
    const targetListeners = listeners.get(target) ?? new Set()
    targetListeners.add(registration)
    listeners.set(target, targetListeners)
    // A new observation reports the current state, so a listener that joins late hears it too.
    observer.unobserve(target)
    observer.observe(target)

    return () => {
      targetListeners.delete(registration)
      if (targetListeners.size > 0 || listeners.get(target) !== targetListeners) {
        return
      }
      listeners.delete(target)
      observer?.unobserve(target)
      if (listeners.size === 0) {
        observer?.disconnect()
        observer = null
      }
    }
  }
}

/** Tell listener each entry of the element in target, until the scope ends. */
export function useObservedElement<Entry>(
  observe: ObserveElement<Entry>,
  target: Readonly<Ref<Element | null>>,
  listener: (entry: Entry) => void
): void {
  let stop: (() => void) | null = null
  watch(
    target,
    (element) => {
      stop?.()
      stop = element === null ? null : observe(element, listener)
    },
    { immediate: true }
  )
  onScopeDispose(() => stop?.())
}
