/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Component, type Ref, getCurrentInstance, h, onErrorCaptured, ref } from 'vue'

import CmkErrorBoundary from './CmkErrorBoundary.vue'
import { type CrashReportState, JavascriptCrashReportApi } from './JavascriptCrashReportApi'

const crashReportApi = new JavascriptCrashReportApi()

function currentComponentName(): string {
  const type = getCurrentInstance()?.type as { name?: string; __name?: string } | undefined
  return type?.name ?? type?.__name ?? ''
}

/**
 * ATTENTION, this might seem that you only catch errors from components
 * inside the <ErrorBoundary>...</ErrorBoundary> tags, but this is not the case!
 *
 * You catch all errors thrown in the component you use useErrorBoundary and
 * of all its child components. Also the <ErrorBoundary> component should be visible
 * all the time, otherwise you may catch an error that is not immediately
 * visible.
 */
export function useCmkErrorBoundary(): {
  CmkErrorBoundary: Component
  error: Ref<Error | null>
  crashReport: Ref<CrashReportState>
} {
  // we use a composeable here, because otherwise we can not catch errors that happen directly
  // in the component, but only from child components.
  const error = ref<Error | null>(null)
  const crashReport = ref<CrashReportState>({ status: 'none' })
  const component = currentComponentName()
  onErrorCaptured((err: Error, _instance, info: string): boolean => {
    console.error(err)
    error.value = err
    crashReport.value = { status: 'storing' }
    void crashReportApi
      .report(err, component, info)
      .then((url: string) => {
        crashReport.value = { status: 'stored', url }
      })
      .catch((reportError: unknown) => {
        console.error('Could not store the error as a crash report', reportError)
        crashReport.value = { status: 'failed' }
      })
    return false
  })
  return {
    CmkErrorBoundary: h(CmkErrorBoundary, { error: error, crashReport: crashReport }),
    error: error,
    crashReport: crashReport
  }
}
