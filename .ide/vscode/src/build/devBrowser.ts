/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { log } from '../core/log'

class DevBrowser {
  private readonly tabs = new Map<string, vscode.Tab>()

  async show(url: string): Promise<void> {
    if (this.alreadyOpen(url)) {
      log(`Browser already open for ${url}; reusing existing window`)
      return
    }
    const before = this.currentTabs()
    await vscode.commands.executeCommand('simpleBrowser.show', url)
    const opened = await this.captureNewTab(before)
    if (opened) {
      this.tabs.set(url, opened)
    }
  }

  private alreadyOpen(url: string): boolean {
    const tracked = this.tabs.get(url)
    if (tracked && this.isOpen(tracked)) {
      return true
    }
    this.tabs.delete(url)
    return this.browserTabs().length > 0
  }

  private browserTabs(): vscode.Tab[] {
    return vscode.window.tabGroups.all
      .flatMap((group) => group.tabs)
      .filter(
        (tab) =>
          tab.input instanceof vscode.TabInputWebview &&
          tab.input.viewType.toLowerCase().includes('browser')
      )
  }

  private currentTabs(): Set<vscode.Tab> {
    return new Set(vscode.window.tabGroups.all.flatMap((group) => group.tabs))
  }

  private isOpen(tab: vscode.Tab): boolean {
    return vscode.window.tabGroups.all.some((group) => group.tabs.includes(tab))
  }

  private captureNewTab(before: Set<vscode.Tab>): Promise<vscode.Tab | undefined> {
    const findNew = (): vscode.Tab | undefined => {
      const added = vscode.window.tabGroups.all
        .flatMap((group) => group.tabs)
        .filter((tab) => !before.has(tab))
      return added.find((tab) => tab.input instanceof vscode.TabInputWebview) ?? added[0]
    }
    const immediate = findNew()
    if (immediate) {
      return Promise.resolve(immediate)
    }
    return new Promise((resolve) => {
      const subscription = vscode.window.tabGroups.onDidChangeTabs(() => {
        const found = findNew()
        if (found) {
          cleanup()
          resolve(found)
        }
      })
      const timer = setTimeout(() => {
        cleanup()
        resolve(findNew())
      }, 3000)
      const cleanup = (): void => {
        subscription.dispose()
        clearTimeout(timer)
      }
    })
  }
}

export const devBrowser = new DevBrowser()
