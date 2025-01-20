/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import axios from 'axios'
import type { AxiosError } from 'axios'
import { CmkError } from '@/lib/error.ts'

import type { MaybeRestApiError, MaybeRestApiCrashReport } from '@/lib/types'
import type { Errors, StageErrors } from '@/lib/rest-api-client/quick-setup/response_schemas'
// import type { Errors, StageErrors } from '@lib/rest./response_types'

export class QuickSetupAxiosError extends CmkError<AxiosError> {
  override name = 'QuickSetupAxiosError'
  override getContext(): string {
    if (axios.isAxiosError(this.cause) && this.cause.response) {
      let moreContext = ''
      if (this.cause.status === 502) {
        moreContext =
          '\n\nThe Checkmk server is temporarily unreachable, possibly due to high load. Please wait ' +
          'a moment and try again.'
      }

      const crashReportUrl = (this.cause.response.data as MaybeRestApiCrashReport).ext?.details
        ?.crash_report_url?.href
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
 * @param err unknown
 * @returns ValidationError | AllStagesValidationError | CmkError<unknown> | QuickSetupAxiosError
 */
export const processError = (
  err: Error
): ValidationError | AllStagesValidationError | CmkError | QuickSetupAxiosError => {
  if (axios.isAxiosError(err)) {
    if (err.response?.status === 400) {
      if (err.response.data?.validation_errors) {
        const responseErrors = err.response.data?.validation_errors
        const responseDetail = err.response.data?.detail
        return {
          type: 'validation',
          formspec_errors:
            responseErrors?.formspec_errors || responseDetail?.formspec_errors || undefined,
          stage_errors: responseErrors?.stage_errors || responseDetail?.stage_errors || undefined
        }
      } else if (err.response.data?.all_stage_errors) {
        return {
          type: 'validation_all_stages',
          all_stage_errors: err.response.data.all_stage_errors,
          formspec_errors: undefined,
          stage_errors: undefined
        }
      } else {
        return {
          type: 'validation',
          stage_errors: err.response.data?.detail,
          formspec_errors: undefined
        }
      }
    } else {
      return new QuickSetupAxiosError(err?.response?.data?.title || err.message, err)
    }
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
