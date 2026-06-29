/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { log } from '../core/log'

interface OpenWindow {
  tab: vscode.Tab
  execution?: vscode.TaskExecution
}

class DevBrowser {
  private readonly windows = new Map<string, OpenWindow>()
  private closeWatcher?: vscode.Disposable

  async show(url: string, execution?: vscode.TaskExecution): Promise<void> {
    this.ensureCloseWatcher()

    const existing = this.windows.get(url)
    if (existing && this.isOpen(existing.tab)) {
      existing.execution = execution
      log(`Browser already open for ${url}; reusing existing window`)
      return
    }
    this.windows.delete(url)

    if (this.browserTabs().length > 0) {
      log(`Browser already open for ${url}; reusing existing window`)
      return
    }

    const before = this.currentTabs()
    await vscode.commands.executeCommand('simpleBrowser.show', url)
    const opened = await this.captureNewTab(before)
    if (opened) {
      this.windows.set(url, { tab: opened, execution })
    }
  }

  private ensureCloseWatcher(): void {
    if (this.closeWatcher) {
      return
    }
    this.closeWatcher = vscode.window.tabGroups.onDidChangeTabs((event) => {
      for (const closed of event.closed) {
        for (const [url, win] of this.windows) {
          if (win.tab === closed) {
            this.windows.delete(url)
            if (win.execution) {
              log(`Browser window for ${url} closed; stopping dev server`)
              win.execution.terminate()
            }
          }
        }
      }
    })
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
