/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'

import client, { unwrap } from '@/lib/rest-api-client/client'

import type { SetDataResult } from '@/form/components/forms/FormSingleChoiceEditableEditAsync.vue'

import type { ValidationMessages } from './validation'

export interface EntityDescription {
  ident: string
  description: string
}

export type Payload = Record<string, unknown>

type SaveResponseData = components['schemas']['EditConfigurationEntityResponse']
type SaveResponseError422 = components['schemas']['Api422DefaultError']

function processSaveResponse(result: {
  data?: SaveResponseData
  error?: object
  response: Response
}): SetDataResult<EntityDescription> {
  try {
    const data = unwrap(result)
    return { type: 'success', entity: { ident: data.id!, description: data.title! } }
  } catch (e) {
    if (result.error && 'status' in result.error && result.error.status === 422) {
      const validationMessages = (result.error as SaveResponseError422).ext!
        .validation_errors as ValidationMessages
      return {
        type: 'error',
        validationMessages
      }
    }
    throw e
  }
}

export const configEntityAPI = {
  getSchema: async (entityType: ConfigEntityType, entityTypeSpecifier: string) => {
    const data = unwrap(
      await client.GET('/domain-types/form_spec/collections/{entity_type}', {
        params: {
          path: { entity_type: entityType },
          query: { entity_type_specifier: entityTypeSpecifier }
        }
      })
    )
    return {
      schema: data.extensions!.schema as FormSpec,
      defaultValues: data.extensions!.default_values as Payload
    }
  },
  getData: async (entityType: ConfigEntityType, entityId: string) => {
    if (entityType === 'folder') {
      throw new Error('Folders are not supported in configEntityAPI.getData')
    }
    if (entityType === 'passwordstore_password') {
      throw new Error('Folders are not supported in configEntityAPI.getData')
    }
    const data = unwrap(
      await client.GET(`/objects/${entityType}/{entity_id}`, {
        params: { path: { entity_id: entityId } }
      })
    )
    return data.extensions as Payload
  },
  listEntities: async (entityType: ConfigEntityType, entityTypeSpecifier: string) => {
    const data = unwrap(
      await client.GET(`/domain-types/${entityType}/collections/{entity_type_specifier}`, {
        params: { path: { entity_type_specifier: entityTypeSpecifier } }
      })
    )
    const values = data.value as { id: string; title: string }[]
    const entities = values.map((entity) => ({
      ident: entity.id,
      description: entity.title
    }))
    return entities
  },
  createEntity: async (
    entityType: ConfigEntityType,
    entityTypeSpecifier: string,
    data: Payload
  ) => {
    const response = await client.POST('/domain-types/configuration_entity/collections/all', {
      params: { header: { 'Content-Type': 'application/json' } },
      body: {
        entity_type: entityType,
        entity_type_specifier: entityTypeSpecifier,
        data
      }
    })
    return await processSaveResponse(response)
  },
  updateEntity: async (
    entityType: ConfigEntityType,
    entityTypeSpecifier: string,
    entityId: string,
    data: Payload
  ) => {
    const response = await client.PUT(
      '/domain-types/configuration_entity/actions/edit-single-entity/invoke',
      {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          entity_type: entityType,
          entity_type_specifier: entityTypeSpecifier,
          entity_id: entityId,
          data
        }
      }
    )
    return await processSaveResponse(response)
  }
}
