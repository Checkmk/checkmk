/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { IconNames } from 'cmk-shared-typing/typescript/icon'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { BurgerMenuCallable, BurgerMenuGraph, BurgerMenuGroup } from '../types'

const _FETCH_CONTEXT_MENU_URL = '/domain-types/graph/actions/fetch_context_menu/invoke'
const _ADD_TO_CONTAINER_URL = '/domain-types/graph/actions/add_to_container/invoke'
const _ADD_TO_VISUAL_URL = '/domain-types/graph/actions/add_to_visual/invoke'

type ExportType = 'graph_export' | 'graph_image'
type ActionType = 'add_to_container' | 'add_to_visual' | 'export'

// The engine and the legacy request disagree on the average's name.
const LEGACY_CONSOLIDATION = { min: 'min', avg: 'average', max: 'max' } as const

export const addToContainer = async (
  pageType: string,
  pageName: string,
  specification: Record<string, unknown>
) => {
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
        specification: specification
      }
    })
  )
}

export const addToVisual = async (
  visualType: string,
  visualName: string,
  specification: Record<string, unknown>
) => {
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
        specification: specification
      }
    })
  )
}

export const graphExport = (page: ExportType, graph: BurgerMenuGraph) => {
  const request = {
    specification: graph.specification,
    consolidation_function: LEGACY_CONSOLIDATION[graph.consolidationFunction],
    time_start: graph.timeStart,
    time_end: graph.timeEnd
  }
  // Same navigation the legacy menu performs; graph_export.py / graph_image.py answer with a
  // Content-Disposition attachment, so the browser downloads it instead of leaving the graph.
  window.location.href = `${page}.py?request=${encodeURIComponent(JSON.stringify(request))}`
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
      return async (graph: BurgerMenuGraph) =>
        await addToContainer(action.parameters[0]!, action.parameters[1]!, graph.specification)

    case 'add_to_visual':
      return async (graph: BurgerMenuGraph) =>
        await addToVisual(action.parameters[0]!, action.parameters[1]!, graph.specification)

    case 'export':
      return async (graph: BurgerMenuGraph) =>
        graphExport(action.parameters[0]! as unknown as ExportType, graph)

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
