import axios from 'axios'
import { GET_QUICK_SETUP_OVERVIEW_URL, VALIDATE_QUICK_SETUP_STAGE_URL } from '@/constants/rest_api'
import { type StageData } from './quick_setup_types'

import {
  type GeneralError,
  type QSInitializationResponse,
  type QSValidateStagesRequest,
  type QSStageResponse,
  type ValidationError
} from './rest_api_types'

// import { ACTIVATE_CHANGES_URL } from '@/constants/ui'
// import { goToUrl } from '@/helpers/url'

/**
 * Returns a record representation of an error to be shown to the user
 * @param err unknown
 * @returns ValidationError | GeneralError
 */

const processError = (err: unknown): ValidationError | GeneralError => {
  if (!axios.isAxiosError(err)) {
    return { type: 'general', general_error: 'Unknown error has ocurred' } as GeneralError
  }

  if (err.response?.status === 400) {
    return { type: 'validation', ...err.response.data?.errors } as ValidationError
  } else {
    return { type: 'general', general_error: err.message } as GeneralError
  }
}

/**
 * Get all stages overview together with the first stage components
 * @param quickSetupId string
 * @returns Promise<QuickSetupOverviewRestApiResponse>
 */
export const getOverview = async (quickSetupId: string): Promise<QSInitializationResponse> => {
  return new Promise((resolve, reject) => {
    const url = GET_QUICK_SETUP_OVERVIEW_URL.replace('{QUICK_SETUP_ID}', quickSetupId)
    axios
      .get(url)
      .then((response) => {
        resolve(response.data)
      })
      .catch((err) => {
        reject(processError(err))
      })
  })
}

export const validateStage = async (
  quickSetupId: string,
  formData: StageData[]
): Promise<QSStageResponse> => {
  return new Promise((resolve, reject) => {
    const url = VALIDATE_QUICK_SETUP_STAGE_URL
    const payload: QSValidateStagesRequest = {
      quick_setup_id: quickSetupId,
      stages: formData.map((stage, index) => ({ stage_id: index + 1, form_data: stage }))
    }

    axios
      .post(url, payload)
      .then((response) => {
        resolve(response.data)
      })
      .catch((err) => {
        reject(processError(err))
      })
  })
}
