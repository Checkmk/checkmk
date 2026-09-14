/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DualListElement } from 'cmk-ui-library/components/CmkDualList'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

const _toElement = (entry: { id?: string; title?: string }): DualListElement => ({
  name: entry.id!,
  title: entry.title!
})

export const getSites = async (): Promise<DualListElement[]> => {
  const data = unwrap(await client.GET('/domain-types/site_connection/collections/all'))
  return data.value.map(_toElement)
}

export const getContactGroups = async (): Promise<DualListElement[]> => {
  const data = unwrap(await client.GET('/domain-types/contact_group_config/collections/all'))
  return (data.value ?? []).map(_toElement)
}
