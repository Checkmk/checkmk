/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api } from '@/lib/api-client'

export interface OAuth2FormData {
  title: string
  authority: string
  tenant_id: string
  client_id: string
  client_secret: unknown
}

export interface MsGraphApiAccessTokenRequestObject {
  id: string
  type: 'ms_graph_api'
  redirect_uri: string
  code: string
  data: OAuth2FormData
}

export interface MsGraphAjaxResponse {
  status: 'success' | 'error'
  message?: string
}

export class Oauth2ConnectionApi extends Api {
  public constructor() {
    super(null, [
      ['Content-Type', 'application/json'],
      ['Accept', 'application/json']
    ])
  }

  public async requestAndSaveAccessToken(
    requestObject: MsGraphApiAccessTokenRequestObject
  ): Promise<MsGraphAjaxResponse> {
    return (await this.post(
      'ajax_request_and_save_ms_graph_access_token.py',
      requestObject
    )) as Promise<MsGraphAjaxResponse>
  }
}
