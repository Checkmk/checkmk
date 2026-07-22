/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { IconNames } from 'cmk-shared-typing/typescript/icon'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { BurgerMenuCallable, BurgerMenuGroup } from '../types'

const _FETCH_CONTEXT_MENU_URL = '/domain-types/graph/actions/fetch_context_menu/invoke'
const _ADD_TO_CONTAINER_URL = '/domain-types/graph/actions/add_to_container/invoke'
const _ADD_TO_VISUAL_URL = '/domain-types/graph/actions/add_to_visual/invoke'
const _EXPORT_URL = '/domain-types/graph/actions/export/invoke'

type ExportType = 'graph_export' | 'graph_image'
type ActionType = 'add_to_container' | 'add_to_visual' | 'export'

export const addToContainer = async (pageType: string, pageName: string, internal: string) => {
  unwrap(
    await client.POST(_ADD_TO_CONTAINER_URL, {
      params: {
        header: {
          'Content-Type': 'application/json'
        }
      },
      body: {
        family: pageType,
        id: pageName,
        internal: internal
      }
    })
  )
}

export const addToVisual = async (visualType: string, visualName: string, internal: string) => {
  unwrap(
    await client.POST(_ADD_TO_VISUAL_URL, {
      params: {
        header: {
          'Content-Type': 'application/json'
        }
      },
      body: {
        family: visualType,
        id: visualName,
        internal: internal
      }
    })
  )
}

export const graphExport = async (page: ExportType, internal: string) => {
  unwrap(
    await client.POST(_EXPORT_URL, {
      params: {
        header: {
          'Content-Type': 'application/json'
        }
      },
      body: {
        target: page,
        internal: internal
      }
    })
  )
}

interface ApiBurgerMenuGroup {
  heading: string
  items: ApiBurgerMenuItem[]
}

interface ApiBurgerMenuItem {
  label: string
  ariaLabel: string
  icon: string
  action: ApiBurgerMenuAction
}

interface ApiBurgerMenuAction {
  id: ActionType
  parameters: string[]
}

const buildCallback = (action: ApiBurgerMenuAction): BurgerMenuCallable => {
  switch (action.id) {
    case 'add_to_container':
      return async (internal: string) =>
        await addToContainer(action.parameters[0]!, action.parameters[1]!, internal)

    case 'add_to_visual':
      return async (internal: string) =>
        await addToVisual(action.parameters[0]!, action.parameters[1]!, internal)

    case 'export':
      return async (internal: string) =>
        await graphExport(action.parameters[0]! as unknown as ExportType, internal)

    default:
      throw new Error(`Unknown action type: ${action.id}`)
  }
}

export const loadMenu = async (addType: string): Promise<BurgerMenuGroup[]> => {
  const groups: ApiBurgerMenuGroup[] = unwrap(
    await client.GET(_FETCH_CONTEXT_MENU_URL, {
      params: {
        query: {
          add_type: addType
        }
      }
    })
  ).value

  return groups.map((group: ApiBurgerMenuGroup) => ({
    heading: group.heading,
    actions: group.items.map((item) => ({
      label: item.label,
      ariaLabel: item.ariaLabel,
      icon: item.icon as IconNames,
      onClick: buildCallback(item.action)
    }))
  }))
}
