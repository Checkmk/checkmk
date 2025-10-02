/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  ChipModeEnum,
  HeaderTriggerModeEnum,
  NavItem,
  NavItemIdEnum,
  NavItemShortcut,
  NavItemTopic,
  NavItems
} from 'cmk-shared-typing/typescript/main_menu'
import { type Ref, ref } from 'vue'

import type { KeyShortcut, KeyShortcutService } from '@/lib/keyShortcuts'
import { ServiceBase } from '@/lib/service/base'

import { MainMenuApiClient } from './main-menu-api-client'
import type {
  MenuItemBadge,
  OnCloseCallback,
  OnNavigateCallback,
  OnShowAllTopic,
  UnackIncompWerksResult,
  UserHintMessages,
  UserPopupMessage
} from './type-defs'

export class MainMenuService extends ServiceBase {
  public currentItem: Ref<NavItem | null> = ref<NavItem | null>(null)
  public showKeyHints: Ref<boolean> = ref<boolean>(false)
  protected showAllTopic = ref<{ id: string; topic: NavItemTopic } | null>(null)
  protected showMoreActive: { [key: string]: Ref<boolean> } = {}
  protected userMessageTrigger: UserHintMessages | null = null
  protected unackIncompWerksTrigger: UnackIncompWerksResult | null = null
  protected userPopupMessages: UserPopupMessage[] = []
  protected itemBadge: { [key: string]: Ref<MenuItemBadge | null> } = {}
  protected api: MainMenuApiClient = new MainMenuApiClient()

  public constructor(
    protected mainItems: NavItems = [],
    protected userItems: NavItems = [],
    shortCutService: KeyShortcutService
  ) {
    super('main-menu-service', shortCutService)
    this.init()
  }

  public toggleKeyHints() {
    this.showKeyHints.value = !this.showKeyHints.value
  }

  public getNavShortCutInfo(shortcut: NavItemShortcut): string {
    const sc: KeyShortcut = {
      key: [shortcut.key],
      alt: shortcut.alt,
      ctrl: shortcut.ctrl,
      shift: shortcut.shift
    }
    return this.shortCutService.getShortCutInfo(sc)
  }

  public isAnyNavItemActive() {
    return this.currentItem.value !== null
  }

  public isNavItemActive(id: NavItemIdEnum) {
    return this.currentItem.value?.id === id
  }

  public navigateIfAnyNavItemIsActive(id: NavItemIdEnum) {
    if (this.isAnyNavItemActive()) {
      this.navigate(id)
    }
  }

  public navigate(id: NavItemIdEnum) {
    this.showKeyHints.value = false
    const item = this.getItemById(id)
    if (this.currentItem.value !== null) {
      this.dispatchCallback('close', this.currentItem.value.id)
    }
    this.currentItem.value = item
    this.dispatchCallback('navigate', item)
  }

  public onNavigate(callback: OnNavigateCallback) {
    this.pushCallBack('navigate', callback)
  }

  public close() {
    const id = this.currentItem.value?.id
    this.currentItem.value = null
    this.dispatchCallback('close', id)
  }

  public onClose(callback: OnCloseCallback) {
    this.pushCallBack('close', callback)
  }

  public setNavItemBadge(id: NavItemIdEnum, badge: MenuItemBadge | null) {
    if (this.itemBadge[id]) {
      this.itemBadge[id].value = badge
    }
  }

  public resetNavItemBadge(id: NavItemIdEnum) {
    this.setNavItemBadge(id, null)
  }

  public getNavItemBadge(id: NavItemIdEnum): MenuItemBadge | null | undefined {
    return this.itemBadge[id]?.value
  }

  public toggleShowMoreLess(id: NavItemIdEnum) {
    if (this.showMoreActive[id]) {
      this.showMoreActive[id].value = !this.showMoreActive[id].value
      void this.api.getToggleShowMoreLess(id, this.showMoreActive[id]?.value ? 'on' : 'off')
    }
  }

  public showMoreIsActive(id: NavItemIdEnum): boolean {
    return this.showMoreActive[id]?.value || false
  }

  public showAllEntriesOfTopic(id: NavItemIdEnum, topic: NavItemTopic) {
    this.dispatchCallback('show-all-topic', id, topic)
  }

  public onShowAllEntriesOfTopic(callback: OnShowAllTopic) {
    this.pushCallBack('show-all-topic', callback)
  }

  public closeShowAllEntriesOfTopic(id: NavItemIdEnum) {
    this.dispatchCallback('close-show-all-topic', id)
  }

  public onCloseShowAllEntriesOfTopic(callback: OnCloseCallback) {
    this.pushCallBack('close-show-all-topic', callback)
  }

  public triggerHeader(mode: HeaderTriggerModeEnum): string | null {
    switch (mode) {
      case 'unack-incomp-werks':
        if (this.unackIncompWerksTrigger && this.unackIncompWerksTrigger.count > 0) {
          return this.unackIncompWerksTrigger.text
        }
        return null
      default:
        return null
    }
  }

  public chipEntry(mode: ChipModeEnum): string | null {
    switch (mode) {
      case 'user-messages-hint':
        if (this.userMessageTrigger && this.userMessageTrigger.count > 0) {
          return `${this.userMessageTrigger.count} ${this.userMessageTrigger.text}`
        }
        return null
      default:
        return null
    }
  }

  public async toggleEntry(mode: string, reload?: boolean) {
    await this.api.postToggleEntry(mode)
    if (reload) {
      location.reload()
    }
  }

  public async markMessageRead(id: NavItemIdEnum) {
    await this.api.markMessageRead(id)
  }

  protected async updateUserMessages() {
    const res = await this.api.getUserMessages()

    this.userMessageTrigger = res.hint_messages
    if (this.userMessageTrigger.count > 0) {
      this.setNavItemBadge('user', {
        content: this.userMessageTrigger.count.toString(),
        color: 'danger'
      })
    }

    this.userPopupMessages = res.popup_messages.map((msg) => {
      msg.title = res.hint_messages.title
      return msg
    })
  }

  protected async updateUnacknowledgedIncompatibleWerks() {
    this.unackIncompWerksTrigger = await this.api.getUnacknowledgedIncompatibleWerks()
    if (this.unackIncompWerksTrigger.count === 0) {
      this.setNavItemBadge('help', null)
    } else {
      this.setNavItemBadge('help', {
        color: 'danger',
        content: this.unackIncompWerksTrigger.count.toString()
      })
    }
  }

  protected getItemById(id: NavItemIdEnum): NavItem {
    const item = [...this.mainItems, ...this.userItems].find((item) => item.id === id)

    if (!item) {
      throw new Error(`NavItem with id "${id}" does not exist`)
    }

    return item
  }

  private init() {
    for (const item of this.mainItems.concat(this.userItems)) {
      this.itemBadge[item.id] = ref<MenuItemBadge | null>(null)

      if (item.show_more) {
        this.showMoreActive[item.id] = ref<boolean>(item.show_more.active)
      }

      if (item.shortcut) {
        this.registerShortCut(
          {
            key: [item.shortcut.key],
            ctrl: item.shortcut.ctrl || false,
            alt: item.shortcut.alt || false,
            shift: item.shortcut.shift || false
          },
          () => {
            if (this.isNavItemActive(item.id)) {
              this.close()
            } else {
              this.navigate(item.id)
            }
          }
        )
      }
    }

    this.registerShortCut({ key: ['Alt'], alt: true }, () => {
      this.toggleKeyHints()
    })
    this.registerShortCut({ key: ['Escape'] }, () => {
      if (this.isAnyNavItemActive()) {
        this.close()
      }
    })
    this.enableShortCuts()

    this.initPeriodicAjax()
  }

  private initPeriodicAjax() {
    void this.updateUserMessages()
    void this.updateUnacknowledgedIncompatibleWerks()
  }
}
