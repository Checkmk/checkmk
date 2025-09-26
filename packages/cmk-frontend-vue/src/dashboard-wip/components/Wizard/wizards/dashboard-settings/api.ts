/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fetchRestAPI } from '@/lib/cmkFetch.ts'

import type { DualListElement } from '@/components/CmkDualList'

const API_ROOT = 'api/unstable'

interface ResponseValueType {
  title: string
  id: string
}

const _getData = async (url: string): Promise<DualListElement[]> => {
  const response = await fetchRestAPI(url, 'GET')
  await response.raiseForStatus()
  const data = await response.json()
  return data.value.map((contactGroup: ResponseValueType) => ({
    name: contactGroup.id,
    title: contactGroup.title
  }))
}

export const getSites = async (): Promise<DualListElement[]> => {
  const url = `${API_ROOT}/domain-types/site_connection/collections/all`
  return _getData(url)
}

export const getContactGroups = async (): Promise<DualListElement[]> => {
  const url = `${API_ROOT}/domain-types/contact_group_config/collections/all`
  return _getData(url)
}
