/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { LabelGroupItem, QueryItem } from './types.ts'

/**
 * Converts QueryItem array to query parameters dictionary
 * @param queryItems - Array of QueryItem objects to convert
 * @param prefix - Prefix for the parameter names (default: "host_labels")
 * @returns Dictionary of query parameters
 *
 * Notes: the structure is still quite different from the original filter structure and may require further adjustments.
 * The essential is covered here and the other filler elements can be handled at the top to accomodate for the
 * valuespec @magic
 */
export function convertToFilterStructure(
  queryItems: QueryItem[],
  prefix: string = 'host_labels'
): Record<string, string> {
  const params: Record<string, string> = {}

  params[`${prefix}_count`] = queryItems.length.toString()

  queryItems.forEach((queryItem, queryIndex) => {
    const queryNum = queryIndex + 1 // 1-indexed

    params[`${prefix}_indexof_${queryNum}`] = queryNum.toString()

    params[`${prefix}_${queryNum}_bool`] = queryItem.operator

    params[`${prefix}_${queryNum}_vs_count`] = queryItem.groups.length.toString()

    queryItem.groups.forEach((group: LabelGroupItem, groupIndex) => {
      const groupNum = groupIndex + 1 // 1-indexed

      params[`${prefix}_${queryNum}_vs_indexof_${groupNum}`] = groupNum.toString()

      params[`${prefix}_${queryNum}_vs_${groupNum}_bool`] = group.operator

      params[`${prefix}_${queryNum}_vs_${groupNum}_vs`] = group.label || ''
    })
  })

  return params
}

/**
 * Converts query parameters dictionary back to QueryItem array structure
 * @param params - Dictionary of query parameters
 * @param prefix - Prefix for the parameter names (default: "host_labels")
 * @returns Array of QueryItem objects
 */
export function convertFromFilterStructure(
  params: Record<string, string | null>,
  prefix: string = 'host_labels'
): QueryItem[] {
  const result: QueryItem[] = []

  // Get the count of query items
  const countKey = `${prefix}_count`
  const count = parseInt(params[countKey] || '0', 10)

  for (let i = 1; i <= count; i++) {
    const operatorKey = `${prefix}_${i}_bool`
    const operator = params[operatorKey] || 'and'

    const groupCountKey = `${prefix}_${i}_vs_count`
    const groupCount = parseInt(params[groupCountKey] || '0', 10)

    const groups: LabelGroupItem[] = []

    for (let j = 1; j <= groupCount; j++) {
      const groupOperatorKey = `${prefix}_${i}_vs_${j}_bool`
      const groupOperator = params[groupOperatorKey] || 'and'

      const labelKey = `${prefix}_${i}_vs_${j}_vs`
      const label = params[labelKey] || null

      groups.push({
        operator: groupOperator,
        label: label
      })
    }

    result.push({
      operator: operator,
      groups: groups
    })
  }
  return result
}
