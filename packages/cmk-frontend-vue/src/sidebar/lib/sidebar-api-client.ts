/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SidebarSnapin } from 'cmk-shared-typing/typescript/sidebar'

import { Api, type ApiResponseBody } from '@/lib/api-client'
import type { AjaxResponse } from '@/lib/main-menu/service/type-defs'

import type { AddSnapinResponse, SidebarSnapinContents } from './type-defs'

// eslint-disable-next-line @typescript-eslint/naming-convention
declare let global_csrf_token: string

export class SidebarApiClient extends Api {
  public constructor() {
    super(null, [
      ['Content-Type', 'application/json'],
      ['Accept', 'application/json']
    ])
  }

  public async getAvailableSidebarSnapins(): Promise<SidebarSnapin[]> {
    return (await this.get(
      `sidebar_ajax_get_available_snapins.py?_csrf_token=${encodeURIComponent(global_csrf_token)}`
    )) as ApiResponseBody<SidebarSnapin[]>
  }

  public async addSidebarSnapin(snapin: SidebarSnapin): Promise<AddSnapinResponse> {
    return (await this.post(
      `sidebar_ajax_add_snapin.py?name=${snapin.name}&_csrf_token=${encodeURIComponent(global_csrf_token)}`
    )) as ApiResponseBody<AddSnapinResponse>
  }

  public async setSidebarSnapinState(name: string, state: 'open' | 'closed' | 'off') {
    return this.post(
      `sidebar_openclose.py?name=${name}&state=${state}&_csrf_token=${encodeURIComponent(global_csrf_token)}`
    )
  }

  public async moveSnapin(name: string, beforeName?: string): Promise<void> {
    const before = beforeName ? `&before=${beforeName}` : ''
    try {
      await this.getRaw(`sidebar_move_snapin.py?name=${name}${before}`)
    } catch {
      // no resonse body = >json parse failes
    }
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
