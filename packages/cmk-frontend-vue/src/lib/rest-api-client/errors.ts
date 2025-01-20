/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkError } from '@/lib/error.ts'
import type { AxiosError } from 'axios'
import axios from 'axios'

import type { Errors, StageErrors } from '@/lib/rest-api-client/quick-setup/response_schemas'
import type { MaybeRestApiCrashReport, MaybeRestApiError } from '@/lib/types'
// import type { Errors, StageErrors } from '@lib/rest./response_types'

export class QuickSetupAxiosError extends CmkError<AxiosError> {
  override name = 'QuickSetupAxiosError'
  override getContext(): string {
    if (axios.isAxiosError<MaybeRestApiCrashReport, unknown>(this.cause) && this.cause.response) {
      let moreContext = ''
      if (this.cause.status === 502) {
        moreContext =
          '\n\nThe Checkmk server is temporarily unreachable, possibly due to high load. Please wait ' +
          'a moment and try again.'
      }

      const crashReportUrl = this.cause.response.data.ext?.details?.crash_report_url?.href
      if (crashReportUrl) {
        moreContext = `${moreContext}\n\nCrash report: ${crashReportUrl}`
      }
      const detail = (this.cause.response.data as MaybeRestApiError).detail
      const title = (this.cause.response.data as MaybeRestApiError).title
      if (detail && title) {
        moreContext = `${moreContext}\n\n${title}: ${detail}`
      }
      return `${this.cause.response.config.method} ${this.cause.response.config.url}\n${this.cause.response.status}: ${this.cause.response.statusText}${moreContext}`
    }
    return ''
  }
}

type OrUndefined<T> = {
  // similar to `Partial`, but explicitly undefined.
  [key in keyof T]: T[key] | undefined
}

export interface RestApiError {
  type: string
}

export interface ValidationError extends RestApiError, OrUndefined<StageErrors> {
  type: 'validation'
}

export interface AllStagesValidationError extends RestApiError, OrUndefined<StageErrors> {
  type: 'validation_all_stages'
  all_stage_errors: Errors[] | undefined
}

/**
 * Returns a record representation of an error to be shown to the user
 * @param err Error
 * @returns CmkError<unknown> | QuickSetupAxiosError
 */
export const argumentError = (err: Error): CmkError | QuickSetupAxiosError => {
  if (axios.isAxiosError<MaybeRestApiError, unknown>(err)) {
    const msg = err.response?.data?.detail || err.response?.data?.title || err.message
    return new QuickSetupAxiosError(msg, err)
  } else {
    return new CmkError('Unknown error has occurred', err)
  }
}

export const isAllStagesValidationError = (value: unknown): value is AllStagesValidationError => {
  return (
    typeof value === 'object' &&
    value !== null &&
    'type' in value &&
    value.type === 'validation_all_stages'
  )
}

export const isValidationError = (value: unknown): value is ValidationError => {
  return (
    typeof value === 'object' && value !== null && 'type' in value && value.type === 'validation'
  )
}
