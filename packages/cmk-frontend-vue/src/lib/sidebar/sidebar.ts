/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SidebarSnapin } from 'cmk-shared-typing/typescript/sidebar'
import { type Ref, ref } from 'vue'

import type { KeyShortcutService } from '../keyShortcuts'
import { ServiceBase } from '../service/base'
import { SidebarApiClient } from './sidebar-api-cleint'
import type { OnUpdateSnapinContent, SidebarSnapinContents } from './type-defs'

export class SidebarService extends ServiceBase {
  protected snapinContents: SidebarSnapinContents = {}
  protected showMoreActive: { [key: string]: Ref<boolean> } = {}
  protected api = new SidebarApiClient()
  protected restart_since: number = 0

  public constructor(
    protected snapins: SidebarSnapin[],
    shortCutService: KeyShortcutService
  ) {
    super('sidebar-service', shortCutService)

    this.init()
  }

  public toggleShowMoreLess(name: string) {
    if (this.showMoreActive[name]) {
      this.showMoreActive[name].value = !this.showMoreActive[name].value
      void this.api.getToggleShowMoreLess(name, this.showMoreActive[name]?.value ? 'on' : 'off')
    }
  }

  public showMoreIsActive(name: string): boolean {
    return this.showMoreActive[name]?.value || false
  }

  public onUpdateSnapinContent(callback: OnUpdateSnapinContent) {
    this.pushCallBack('update-snapin-content', callback)
  }

  public getSnapinContent(name: string): Promise<string> {
    return new Promise((resolve) => {
      this.awaitSnapinContent(name, resolve)
    })
  }

  public getSnapinByName(name: string): SidebarSnapin | null {
    for (const s of this.snapins) {
      if ((s.name = name)) {
        return s
      }
    }
    return null
  }

  public refreshesOnRestart(name: string): boolean {
    return this.getSnapinByName(name)?.refresh_on_restart === true
  }

  public refreshesRegularly(name: string): boolean {
    return this.getSnapinByName(name)?.refresh_regularly === true
  }

  protected awaitSnapinContent(
    name: string,
    resolve: (value: string | PromiseLike<string>) => void
  ) {
    if (this.snapinContents[name]) {
      resolve(this.snapinContents[name])
    } else {
      setTimeout(() => {
        this.awaitSnapinContent(name, resolve)
      }, 200)
    }
  }

  protected async updateSnapinContent(names: string[]) {
    const contents = await this.api.getSidebarSnapinContents(names, this.restart_since)
    this.restart_since = Math.floor(new Date().getTime() / 1000)

    for (const key of Object.keys(contents)) {
      if (this.snapinContents[key]) {
        if (typeof contents[key] === 'string') {
          if (contents[key] === '' || this.refreshesOnRestart(key)) {
            delete contents[key]
            continue
          }
          this.snapinContents[key] = contents[key]
        }
      }
    }
    this.dispatchCallback('update-snapin-content', contents)
  }

  private init() {
    for (const s of this.snapins) {
      this.snapinContents[s.name] = null

      if (s.has_show_more_items) {
        this.showMoreActive[s.name] = ref<boolean>(s.show_more_active || false)
      }
    }

    void this.updateSnapinContent(this.snapins.map((s) => s.name))
    this.initPeriodically()
  }

  private initPeriodically() {
    setInterval(() => {
      console.log('exec update')
      void this.updateSnapinContent(
        this.snapins.filter((s) => s.refresh_on_restart || s.refresh_on_restart).map((s) => s.name)
      )
    }, 30000)
  }
}
