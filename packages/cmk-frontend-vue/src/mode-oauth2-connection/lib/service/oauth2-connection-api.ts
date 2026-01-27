/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api } from '@/lib/api-client'

import type { SetDataResult } from '@/form/FormEditAsync.vue'
import {
  type EntityDescription,
  type Payload,
  configEntityAPI
} from '@/form/private/forms/FormSingleChoiceEditable/configuration_entity'

export interface OAuth2FormData {
  ident: string
  title: string
  authority: string
  tenant_id: string
  client_id: string
  client_secret: unknown
  access_token?: string
  refresh_token?: string
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
  data?: {
    access_token: string
    refresh_token: string
  }
}

export class Oauth2ConnectionApi extends Api {
  public constructor() {
    super(null, [
      ['Content-Type', 'application/json'],
      ['Accept', 'application/json']
    ])
  }

  public async requestAccessToken(
    requestObject: MsGraphApiAccessTokenRequestObject
  ): Promise<MsGraphAjaxResponse> {
    return (await this.post(
      'ajax_request_ms_graph_access_token.py',
      requestObject
    )) as Promise<MsGraphAjaxResponse>
  }

  public async saveOAuth2Connection(
    requestObject: OAuth2FormData,
    entityTypeSpecifier: 'microsoft_entra_id'
  ): Promise<SetDataResult<EntityDescription>> {
    return await configEntityAPI.createEntity(
      'oauth2_connection',
      entityTypeSpecifier,
      requestObject as unknown as Payload
    )
  }

  public async updateOAuth2Connection(
    ident: string,
    requestObject: OAuth2FormData,
    entityTypeSpecifier: 'microsoft_entra_id'
  ): Promise<SetDataResult<EntityDescription>> {
    return await configEntityAPI.updateEntity(
      'oauth2_connection',
      entityTypeSpecifier,
      ident,
      requestObject as unknown as Payload
    )
  }
}
