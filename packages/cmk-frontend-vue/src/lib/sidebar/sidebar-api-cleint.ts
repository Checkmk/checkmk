/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api } from '@/lib/api-client'

import type { AjaxResponse } from '../main-menu/service/type-defs'
import type { SidebarSnapinContents } from './type-defs'

export class SidebarApiClient extends Api {
  public constructor() {
    super(null, [
      ['Content-Type', 'application/json'],
      ['Accept', 'application/json']
    ])
  }

  public async getSidebarSnapinContents(
    names: string[],
    since: number
  ): Promise<SidebarSnapinContents> {
    const res = (await this.getRaw(
      `sidebar_snapin.py?names=${names.join(',')}&since=${since}`
    )) as string[]

    const snapinContents: SidebarSnapinContents = {}
    names.forEach((name, i) => {
      snapinContents[name] = res[i] as string
    })

    return snapinContents
  }

  public async getToggleShowMoreLess(
    name: string,
    state: 'on' | 'off'
  ): Promise<AjaxResponse<null>> {
    return (await this.get(
      'tree_openclose.py?tree=more_buttons' + `&name=sidebar_snapin_${name}` + `&state=${state}`
    )) as AjaxResponse<null>
  }
}
