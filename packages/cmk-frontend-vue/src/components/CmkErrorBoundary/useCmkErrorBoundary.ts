/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Component, type Ref, h, onErrorCaptured, ref } from 'vue'

import CmkErrorBoundary from './CmkErrorBoundary.vue'

/**
 * ATTENTION, this might seem that you only catch errors from components
 * inside the <ErrorBoundary>...</ErrorBoundary> tags, but this is not the case!
 *
 * You catch all errors thrown in the component you use useErrorBoundary and
 * of all its child components. Also the <ErrorBoundary> component should be visible
 * all the time, otherwise you may catch an error that is not immediately
 * visible.
 */
export function useCmkErrorBoundary(): { CmkErrorBoundary: Component; error: Ref<Error | null> } {
  // we use a composeable here, because otherwise we can not catch errors that happen directly
  // in the component, but only from child components.
  const error = ref<Error | null>(null)
  onErrorCaptured((err: Error): boolean => {
    console.error(err)
    error.value = err
    return false
  })
  return {
    CmkErrorBoundary: h(CmkErrorBoundary, { error: error }),
    error: error
  }
}
