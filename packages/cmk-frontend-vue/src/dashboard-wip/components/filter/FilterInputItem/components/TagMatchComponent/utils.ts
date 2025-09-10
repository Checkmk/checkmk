/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export interface TagMatchItem {
  group: string | null
  operator: string
  value: string | null
}

/**
 * Converts an array of TagMatchItem objects to the original flat dictionary format
 * @param items - Array of TagMatchItem objects
 * @param variablePrefix - The prefix to use for generating keys
 * @returns Record with flattened key-value pairs
 */
export function tagMatchItemsToDict(
  items: TagMatchItem[],
  variablePrefix: string
): Record<string, string | null> {
  const result: Record<string, string | null> = {}

  items.forEach((item, index) => {
    const groupKey = `${variablePrefix}_${index}_grp`
    const operatorKey = `${variablePrefix}_${index}_op`
    const valueKey = `${variablePrefix}_${index}_val`

    result[groupKey] = item.group
    result[operatorKey] = item.operator
    result[valueKey] = item.value
  })

  return result
}

/**
 * Converts the original flat dictionary format to an array of TagMatchItem objects
 * Only creates items for indices where an operator key exists
 * @param dict - Record with flattened key-value pairs
 * @param variablePrefix - The prefix used in the dictionary keys
 * @returns Array of TagMatchItem objects
 */
export function dictToTagMatchItems(
  dict: Record<string, string | null>,
  variablePrefix: string
): TagMatchItem[] {
  const items: TagMatchItem[] = []
  const indices = new Set<number>()

  // Find indices that have operator keys (these determine which rows exist)
  Object.keys(dict).forEach((key) => {
    if (key.startsWith(`${variablePrefix}_`) && key.endsWith('_op')) {
      const suffix = key.substring(variablePrefix.length + 1) // Remove prefix and underscore
      const indexStr = suffix.substring(0, suffix.length - 3) // Remove '_op' suffix

      if (!isNaN(Number(indexStr))) {
        indices.add(parseInt(indexStr, 10))
      }
    }
  })

  // Sort indices to maintain order
  const sortedIndices = Array.from(indices).sort((a, b) => a - b)

  sortedIndices.forEach((index) => {
    const groupKey = `${variablePrefix}_${index}_grp`
    const operatorKey = `${variablePrefix}_${index}_op`
    const valueKey = `${variablePrefix}_${index}_val`

    items.push({
      group: dict[groupKey] || null,
      operator: dict[operatorKey] || 'is',
      value: dict[valueKey] || null
    })
  })

  return items
}
