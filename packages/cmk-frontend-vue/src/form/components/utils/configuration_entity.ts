/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'
import type { SetDataResult } from '@/form/components/forms/FormSingleChoiceEditableEditAsync.vue'

import { cmkFetch, type CmkFetchResponse } from '@/lib/cmkFetch'

export interface EntityDescription {
  ident: string
  description: string
}

export type Payload = Record<string, unknown>

const API_ROOT = 'api/1.0'

const GET_CONFIG_ENTITY_SCHEMA = (entityType: ConfigEntityType, entityTypeSpecifier: string) =>
  `${API_ROOT}/domain-types/form_spec/collections/${entityType}?entity_type_specifier=${entityTypeSpecifier}`
/* TODO the way we define a new collection for every entity type risks a name clash with rulespecs for example. */
const GET_CONFIG_ENTITY_DATA = (entityType: ConfigEntityType, entityId: string) =>
  `${API_ROOT}/objects/${entityType}/${entityId}`
const LIST_CONFIG_ENTITIES = (entityType: ConfigEntityType, entityTypeSpecifier: string) =>
  `${API_ROOT}/domain-types/${entityType}/collections/${entityTypeSpecifier}`
const CREATE_CONFIG_ENTITY = `${API_ROOT}/domain-types/configuration_entity/collections/all`
const UPDATE_CONFIG_ENTITY = `${API_ROOT}/domain-types/configuration_entity/actions/edit-single-entity/invoke`

const fetchRestAPI = async (url: string, method: string, body?: Payload) => {
  const params: RequestInit = {
    method,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    }
  }
  if (body) {
    params.body = JSON.stringify(body)
  }
  const response = await cmkFetch(url, params)
  return response
}

async function processSaveResponse(
  response: CmkFetchResponse
): Promise<SetDataResult<EntityDescription>> {
  const returnData = await response.json()
  if (response.status === 422) {
    return { type: 'error', validationMessages: returnData.ext.validation_errors }
  }
  await response.raiseForStatus()
  /* TODO: Handle generic errors everywhere*/
  return { type: 'success', entity: { ident: returnData.id, description: returnData.title } }
}

export const configEntityAPI = {
  getSchema: async (entityType: ConfigEntityType, entityTypeSpecifier: string) => {
    const response = await fetchRestAPI(
      GET_CONFIG_ENTITY_SCHEMA(entityType, entityTypeSpecifier),
      'GET'
    )
    await response.raiseForStatus()
    const data = await response.json()
    return { schema: data.extensions.schema, defaultValues: data.extensions.default_values }
  },
  getData: async (entityType: ConfigEntityType, entityId: string) => {
    const response = await fetchRestAPI(GET_CONFIG_ENTITY_DATA(entityType, entityId), 'GET')
    const data = await response.json()
    await response.raiseForStatus()
    return data.extensions
  },
  /* TODO we should use an openAPI-generated client here */
  listEntities: async (entityType: ConfigEntityType, entityTypeSpecifier: string) => {
    const response = await fetchRestAPI(
      LIST_CONFIG_ENTITIES(entityType, entityTypeSpecifier),
      'GET'
    )
    const values: { id: string; title: string }[] = await response.json()
    await response.raiseForStatus()
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
    const response = await fetchRestAPI(CREATE_CONFIG_ENTITY, 'POST', {
      entity_type: entityType,
      entity_type_specifier: entityTypeSpecifier,
      data
    })
    return await processSaveResponse(response)
  },
  updateEntity: async (
    entityType: ConfigEntityType,
    entityTypeSpecifier: string,
    entityId: string,
    data: Payload
  ) => {
    const response = await fetchRestAPI(UPDATE_CONFIG_ENTITY, 'PUT', {
      entity_type: entityType,
      entity_type_specifier: entityTypeSpecifier,
      entity_id: entityId,
      data
    })
    return await processSaveResponse(response)
  }
}
