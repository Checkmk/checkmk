/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { type SettingsEntry, applySettings, installExtensions } from '../build/settings'
import {
  type ExtensionSets,
  getExtensionIds,
  getOptionalFamilies,
  getRequiredFamilies,
  isDefaultPicked
} from '../core/config'
import { log } from '../core/log'

interface FamilyPickItem extends vscode.QuickPickItem {
  familyName: string
  picked?: boolean
  isRequired?: boolean
}

const DISPLAY_NAMES: Record<string, string> = {
  frontend: 'UI'
}

function displayName(name: string): string {
  return DISPLAY_NAMES[name] || name.charAt(0).toUpperCase() + name.slice(1)
}

async function pickFamilies(
  title: string,
  extensionSets: ExtensionSets,
  filterFamilies?: string[]
): Promise<string[] | null> {
  const requiredFamilies = getRequiredFamilies(extensionSets)
  const optionalFamilies = (filterFamilies || getOptionalFamilies(extensionSets)).filter(
    (name) => !requiredFamilies.includes(name)
  )

  const allItem: FamilyPickItem = {
    label: '$(checklist) All',
    description: `Select all ${optionalFamilies.length} optional families`,
    familyName: '__all__',
    picked: false
  }

  const requiredItems: FamilyPickItem[] = requiredFamilies.map((name) => ({
    label: `$(lock) ${displayName(name)}`,
    description: `${getExtensionIds(extensionSets, name).length} extensions — required`,
    familyName: name,
    picked: true,
    isRequired: true
  }))

  const optionalItems: FamilyPickItem[] = optionalFamilies.map((name) => ({
    label: `$(package) ${displayName(name)}`,
    description: `${getExtensionIds(extensionSets, name).length} extensions`,
    familyName: name,
    picked: isDefaultPicked(extensionSets, name),
    isRequired: false
  }))

  const items: (FamilyPickItem | vscode.QuickPickItem)[] = []
  if (requiredItems.length > 0) {
    items.push({ label: 'Required', kind: vscode.QuickPickItemKind.Separator })
    items.push(...requiredItems)
  }
  items.push({ label: 'Optional', kind: vscode.QuickPickItemKind.Separator })
  items.push(allItem)
  items.push(...optionalItems)

  const selectableItems = [...requiredItems, allItem, ...optionalItems]

  const selected = await new Promise<string[] | null>((resolve) => {
    let resolved = false
    const picker = vscode.window.createQuickPick<FamilyPickItem>()
    picker.title = title
    picker.placeholder = 'Required families are locked. Select optional families, then press Enter'
    picker.items = selectableItems
    picker.selectedItems = selectableItems.filter((i) => i.picked)
    picker.canSelectMany = true

    let prevHasAll = false
    picker.onDidChangeSelection((selection) => {
      const missingRequired = requiredItems.filter(
        (req) => !selection.some((s) => s.familyName === req.familyName)
      )
      if (missingRequired.length > 0) {
        picker.selectedItems = [...selection, ...missingRequired]
        return
      }

      const hasAll = selection.some((i) => i.familyName === '__all__')
      if (hasAll && !prevHasAll) {
        picker.selectedItems = selectableItems
      } else if (!hasAll && prevHasAll) {
        picker.selectedItems = requiredItems
      }
      prevHasAll = hasAll
    })

    picker.onDidAccept(() => {
      resolved = true
      const sel = [...picker.selectedItems]
        .filter((i) => i.familyName && i.familyName !== '__all__')
        .map((i) => i.familyName)
      picker.hide()
      resolve(sel)
    })

    picker.onDidHide(() => {
      picker.dispose()
      if (!resolved) resolve(null)
    })

    picker.show()
  })

  return selected
}

export function registerIdePickers(
  context: vscode.ExtensionContext,
  extensionSets: ExtensionSets,
  settingsSets: Record<string, SettingsEntry>
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.installPicker', async () => {
      const selected = await pickFamilies('CMK ▸ IDE: Install Extensions', extensionSets)
      if (!selected || selected.length === 0) return
      log(`Install extensions: ${selected.join(', ')}`)
      for (const name of selected) {
        await installExtensions(displayName(name), getExtensionIds(extensionSets, name))
      }
    })
  )

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.configurePicker', async () => {
      const familiesWithSettings = Object.keys(settingsSets)
      const selected = await pickFamilies(
        'CMK ▸ IDE: Configure Settings',
        extensionSets,
        familiesWithSettings
      )
      if (!selected || selected.length === 0) return
      log(`Configure settings: ${selected.join(', ')}`)
      for (const name of selected) {
        if (settingsSets[name]) {
          await applySettings(displayName(name), settingsSets[name], false, extensionSets)
        }
      }
    })
  )

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.setupPicker', async () => {
      const selected = await pickFamilies('CMK ▸ IDE: Setup (Install + Configure)', extensionSets)
      if (!selected || selected.length === 0) return
      log(`IDE setup: ${selected.join(', ')}`)
      for (const name of selected) {
        await installExtensions(displayName(name), getExtensionIds(extensionSets, name))
        if (settingsSets[name]) {
          await applySettings(displayName(name), settingsSets[name], false, extensionSets)
        }
      }
    })
  )
}
