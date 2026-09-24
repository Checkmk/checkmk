/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DualListElement } from 'cmk-ui-library/components/CmkDualList'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

export const getSites = async (): Promise<DualListElement[]> => {
  const data = unwrap(await client.GET('/domain-types/site_connection/collections/all'))
  return data.value.map((entry) => ({ name: entry.id!, title: entry.title }))
}

// The contact group endpoint is still a Marshmallow one, so its title stays
// optional in the generated type even though it is always set.
export const getContactGroups = async (): Promise<DualListElement[]> => {
  const data = unwrap(await client.GET('/domain-types/contact_group_config/collections/all'))
  return (data.value ?? []).map((entry) => ({ name: entry.id!, title: entry.title! }))
}
