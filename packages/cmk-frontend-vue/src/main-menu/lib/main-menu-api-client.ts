/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api } from '@/lib/api-client'

import type { AjaxResponse, UnackIncompWerksResult, UserMessagesResult } from './type-defs'

// eslint-disable-next-line @typescript-eslint/naming-convention
declare let global_csrf_token: string

export class MainMenuApiClient extends Api {
  public constructor() {
    super(null, [
      ['Content-Type', 'application/json'],
      ['Accept', 'application/json']
    ])
  }

  public async getToggleShowMoreLess(id: string, state: 'on' | 'off'): Promise<AjaxResponse<null>> {
    return (await this.get(
      'tree_openclose.py?tree=more_buttons' + `&name=main_menu_${id}` + `&state=${state}`
    )) as AjaxResponse<null>
  }

  public async postToggleEntry(mode: string): Promise<void> {
    await this.post(mode, {
      _csrf_token: encodeURIComponent(global_csrf_token)
    })
  }

  public async getUserMessages(): Promise<UserMessagesResult> {
    return (await this.get('ajax_sidebar_get_messages.py')) as UserMessagesResult
  }

  public async markMessageRead(id: string): Promise<void> {
    await this.get(`sidebar_message_read.py?id=${id}`)
  }

  public async getUnacknowledgedIncompatibleWerks(): Promise<UnackIncompWerksResult> {
    return (await this.get('ajax_sidebar_get_unack_incomp_werks.py')) as UnackIncompWerksResult
  }
}
