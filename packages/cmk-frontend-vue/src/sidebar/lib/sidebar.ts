/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SidebarSnapin } from 'cmk-shared-typing/typescript/sidebar'
import { type Ref, ref } from 'vue'

import type { KeyShortcutService } from '@/lib/keyShortcuts'
import { ServiceBase } from '@/lib/service/base'

import { SidebarApiClient } from './sidebar-api-client'
import type { OnUpdateSnapinContent, SidebarSnapinContents } from './type-defs'

const active = ref<boolean>(true)
export class SidebarService extends ServiceBase {
  public snapinsRef = ref<SidebarSnapin[]>([])
  protected snapinContents: SidebarSnapinContents = {}
  protected showMoreActive: { [key: string]: Ref<boolean> } = {}
  protected api = new SidebarApiClient()
  protected restart_since: number = 0

  public constructor(
    protected snapins: SidebarSnapin[],
    protected updateInterval: number,
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

  public async getAvailableSnapins(): Promise<SidebarSnapin[]> {
    const snapins = await this.api.getAvailableSidebarSnapins()

    const contents: SidebarSnapinContents = {}

    for (const s of snapins) {
      if (s.content) {
        this.snapinContents[s.name] = contents[s.name] = s.content
      }
    }

    setTimeout(() => {
      this.dispatchCallback('update-snapin-content', contents)
    })

    return snapins
  }

  public async persistSnapinToggleState(name: string, state: 'open' | 'closed') {
    return this.api.setSidebarSnapinState(name, state)
  }

  public async addSnapin(snapin: SidebarSnapin): Promise<void> {
    const res = await this.api.addSidebarSnapin(snapin)

    this.snapins.push(snapin)
    this.setSnapinsRef()

    const contents: SidebarSnapinContents = {}
    this.snapinContents[snapin.name] = contents[snapin.name] = res.content

    setTimeout(() => {
      this.dispatchCallback('update-snapin-content', contents)
    })
  }

  public async removeSnapin(name: string): Promise<void> {
    await this.api.setSidebarSnapinState(name, 'off')
    this.snapins = this.snapins.filter((s) => s.name !== name)
    this.setSnapinsRef()
  }

  public async moveSnapin(initIndex: number, endIndex: number): Promise<void> {
    if (initIndex + 1 === endIndex) {
      return
    }

    const movedSnapin = this.snapins[initIndex]
    let beforeSnapin = this.snapins[endIndex]
    let beforeIndex = endIndex

    if (initIndex < endIndex) {
      beforeSnapin = this.snapins[endIndex - 1]
      beforeIndex = endIndex - 1
    }

    if (movedSnapin) {
      const snapins = this.snapins.filter((s) => s.name !== movedSnapin.name)

      if (beforeSnapin) {
        snapins.splice(beforeIndex, 0, movedSnapin)
      } else {
        snapins.push(movedSnapin)
      }

      this.snapins = snapins
      this.setSnapinsRef()

      await this.api.moveSnapin(movedSnapin.name, beforeSnapin?.name)
    }
  }

  public refreshesOnRestart(name: string): boolean {
    return this.getSnapinByName(name)?.refresh_on_restart === true
  }

  public refreshesRegularly(name: string): boolean {
    return this.getSnapinByName(name)?.refresh_regularly === true
  }

  public static toggle(): void {
    active.value = !active.value
    const container = document.getElementById('sidebar')
    if (container) {
      if (active.value) {
        container?.classList.add('unfolded')
      } else {
        container?.classList.remove('unfolded')
      }
    }
  }

  public static isActive(): boolean {
    return active.value
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

  public async updateSnapinContent(names: string[]) {
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

  private setSnapinsRef() {
    this.snapinsRef.value = this.snapins.slice()
  }

  private init() {
    this.setSnapinsRef()
    for (const s of this.snapins) {
      this.snapinContents[s.name] = null

      if (s.has_show_more_items) {
        this.showMoreActive[s.name] = ref<boolean>(s.show_more_active || false)
      }
    }

    this.registerShortCut(
      {
        key: ['/'],
        ctrl: true
      },
      SidebarService.toggle
    )
    this.registerShortCut(
      {
        key: ['/'],
        ctrl: true,
        shift: true
      },
      SidebarService.toggle
    )

    this.enableShortCuts()

    void this.updateSnapinContent(this.snapins.map((s) => s.name))
    this.initPeriodically()
  }

  private initPeriodically() {
    setInterval(() => {
      void this.updateSnapinContent(
        this.snapins.filter((s) => s.refresh_on_restart || s.refresh_on_restart).map((s) => s.name)
      )
    }, this.updateInterval * 1000)
  }
}
