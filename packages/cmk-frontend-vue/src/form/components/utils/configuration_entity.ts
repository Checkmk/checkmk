/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfigEntityType } from '@/form/components/configuration_entity'
import type { FormSpec, ValidationMessage } from '../vue_formspec_components'

export interface EntityDescription {
  ident: string
  description: string
}

export type SetDataResult =
  | { type: 'success'; entity: EntityDescription }
  | { type: 'error'; validationMessages: Array<ValidationMessage> }

export type Payload = Record<string, unknown>

export interface API {
  getSchema: () => Promise<{ schema: FormSpec; defaultValues: Payload }>
  getData: (entityId: string) => Promise<Payload>
  createEntity: (data: Payload) => Promise<SetDataResult>
  updateEntity: (update: string, data: Payload) => Promise<SetDataResult>
  listEntities: () => Promise<EntityDescription[]>
}

const API_ROOT = 'api/1.0'

const GET_CONFIG_ENTITY_SCHEMA = (entityType: ConfigEntityType, entityTypeSpecifier: string) =>
  `${API_ROOT}/domain-types/form_spec/collections/${entityType}?entity_type_specifier=${entityTypeSpecifier}`
/* TODO the way we define a new collection for every entity type risks a name clash with rulespecs for example. */
const GET_CONFIG_ENTITY_DATA = (entityType: ConfigEntityType, entityId: string) =>
  `${API_ROOT}/objects/${entityType}/${entityId}`
const LIST_CONFIG_ENTITIES = (entityType: ConfigEntityType) =>
  `${API_ROOT}/domain-types/${entityType}/collections/all`
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
  const response = await fetch(url, params)
  return response
}

async function processSaveResponse(response: Response): Promise<SetDataResult> {
  const returnData = await response.json()
  if (response.status === 422) {
    return { type: 'error', validationMessages: returnData.ext.validation_errors }
  }
  /* TODO: Handle generic errors everywhere*/
  return { type: 'success', entity: { ident: returnData.id, description: returnData.title } }
}

export function getConfigEntityAPI({
  entityType,
  entityTypeSpecifier
}: {
  /**
   * The type of the entity to be managed, e.g., "notification_parameter"
   */
  entityType: ConfigEntityType
  /**
   * The specifier of the entity to be managed, e.g., "mail"
   */
  entityTypeSpecifier: string
}): API {
  const getSchema = async () => {
    const response = await fetchRestAPI(
      GET_CONFIG_ENTITY_SCHEMA(entityType, entityTypeSpecifier),
      'GET'
    )
    const data = await response.json()
    return { schema: data.extensions.schema, defaultValues: data.extensions.default_values }
  }
  const getData = async (entityId: string) => {
    const response = await fetchRestAPI(GET_CONFIG_ENTITY_DATA(entityType, entityId), 'GET')
    const data = await response.json()
    return data.extensions
  }
  /* TODO we should use an openAPI-generated client here */
  const listEntities = async () => {
    const response = await fetchRestAPI(LIST_CONFIG_ENTITIES(entityType), 'GET')
    const data = await response.json()
    return data.value.map((entity: { id: string; title: string }) => ({
      ident: entity.id,
      description: entity.title
    }))
  }

  const createEntity = async (data: Payload) => {
    const response = await fetchRestAPI(CREATE_CONFIG_ENTITY, 'POST', {
      entity_type: entityType,
      entity_type_specifier: entityTypeSpecifier,
      data
    })
    return await processSaveResponse(response)
  }
  const updateEntity = async (entityId: string, data: Payload) => {
    const response = await fetchRestAPI(UPDATE_CONFIG_ENTITY, 'PUT', {
      entity_type: entityType,
      entity_type_specifier: entityTypeSpecifier,
      entity_id: entityId,
      data
    })
    return await processSaveResponse(response)
  }

  return { getSchema, getData, listEntities, createEntity, updateEntity }
}
