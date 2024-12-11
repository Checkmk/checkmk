/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import axios from 'axios'
import type { AxiosError } from 'axios'
import { CmkError } from '@/components/CmkError'
import type {
  ValidationError,
  AllStagesValidationError,
  MaybeRestApiError,
  MaybeRestApiCrashReport
} from './types'

class QuickSetupAxiosError extends CmkError<AxiosError> {
  override name = 'QuickSetupAxiosError'
  override getContext(): string {
    if (axios.isAxiosError(this.cause) && this.cause.response) {
      let moreContext = ''
      const crashReportUrl = (this.cause.response.data as MaybeRestApiCrashReport).ext?.details
        ?.crash_report_url?.href
      if (crashReportUrl) {
        moreContext = `\n\nCrash report: ${crashReportUrl}`
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

/**
 * Returns a record representation of an error to be shown to the user
 * @param err unknown
 * @returns ValidationError | AllStagesValidationError
 */
export const processError = (
  err: unknown
): ValidationError | AllStagesValidationError | CmkError<unknown> | QuickSetupAxiosError => {
  if (axios.isAxiosError(err)) {
    if (err.response?.status === 400) {
      if (err.response.data?.errors) {
        const responseErrors = err.response.data?.errors
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
