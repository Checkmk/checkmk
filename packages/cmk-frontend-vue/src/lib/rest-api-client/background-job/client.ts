/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import axios from 'axios'
import { API_ROOT } from '../constants'
import type { BackgroundJobSnapshotObject } from './response_schemas'

const API_DOMAIN = 'background_job'
/**
 * Show the last status of a background job
 * @param jobId string
 * @returns Promise<BackgroundJobSnapshotObject>
 */
export const get = async (jobId: string): Promise<BackgroundJobSnapshotObject> => {
  const url = `${API_ROOT}/objects/${API_DOMAIN}/${jobId}`
  const { data } = await axios.get(url)
  return data
}
