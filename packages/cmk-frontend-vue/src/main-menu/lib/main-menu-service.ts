/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  ChipModeEnum,
  HeaderTriggerModeEnum,
  NavItem,
  NavItemBadge,
  NavItemIdEnum,
  NavItemShortcut,
  NavItemTopic,
  NavItemTopicEntry,
  NavItems,
  NavLinkItem
} from 'cmk-shared-typing/typescript/main_menu'
import { type Ref, ref } from 'vue'

import { type KeyShortcut, KeyShortcutService } from '@/lib/keyShortcuts'
import { ServiceBase } from '@/lib/service/base'

import { MainMenuApiClient } from './main-menu-api-client'
import type {
  MenuItemBadge,
  NumberOfPendingChangesResponse,
  OnCloseCallback,
  OnNavigateCallback,
  OnShowAllTopic,
  OnUserPopupMessagesCallback,
  UnackIncompWerksResult,
  UserHintMessages,
  UserPopupMessageRef
} from './type-defs'

export class MainMenuService extends ServiceBase {
  public currentItem: Ref<NavItem | null> = ref<NavItem | null>(null)
  public showKeyHints: Ref<boolean> = ref<boolean>(false)
  protected showAllTopic = ref<{ id: string; topic: NavItemTopic } | null>(null)
  protected showMoreActive: { [key: string]: Ref<boolean> } = {}
  protected userMessageTrigger: UserHintMessages | null = null
  protected unackIncompWerksTrigger: UnackIncompWerksResult | null = null
  protected userPopupMessages: UserPopupMessageRef[] = []
  protected itemBadge: { [key: string]: Ref<MenuItemBadge | null> } = {}
  protected api: MainMenuApiClient = new MainMenuApiClient()
  private badgeUpdateTimeouts: Map<string, ReturnType<typeof setTimeout>> = new Map()

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
    return KeyShortcutService.getShortCutInfo(sc)
  }

  public isAnyNavItemActive() {
    return this.currentItem.value !== null
  }

  public isNavItemActive(id: NavItemIdEnum) {
    return this.currentItem.value?.id === id
  }

  public navigate(id: NavItemIdEnum) {
    this.showKeyHints.value = false
    const item = this.getItemById(id)

    if (item.type === 'item') {
      if (this.currentItem.value !== null) {
        this.dispatchCallback('close', this.currentItem.value.id)
      }
      this.currentItem.value = item
      this.dispatchCallback('navigate', item)
    } else {
      this.currentItem.value = null
    }
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

  private focusAdjacentEntry(direction: 1 | -1) {
    const current = this.currentItem.value
    if (!current || current.vue_app) {
      return
    }

    const container = document.getElementById(`main_menu_${current.id}`)
    if (!container) {
      return
    }

    const entries = Array.from(container.querySelectorAll<HTMLAnchorElement>('a[href]')).filter(
      (entry) => entry.offsetParent !== null && !entry.closest('.mm-default-popup__header')
    )
    if (entries.length === 0) {
      return
    }

    const currentIndex = entries.indexOf(document.activeElement as HTMLAnchorElement)
    const nextIndex =
      currentIndex === -1
        ? direction === 1
          ? 0
          : entries.length - 1
        : (currentIndex + direction + entries.length) % entries.length

    entries[nextIndex]?.focus()
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

  public showAllEntriesOfTopic(id: NavItemIdEnum, topic: NavItemTopic | NavItemTopicEntry) {
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

  public async markMessageRead(msgId: string) {
    await this.api.markMessageRead(msgId)
  }

  public onUserPopupMessages(callback: OnUserPopupMessagesCallback) {
    this.pushCallBack('user-popup-messages', callback)
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
      return {
        id: msg.id,
        text: msg.text,
        title: res.hint_messages.title,
        open: ref<boolean>(true)
      }
    })

    if (this.userPopupMessages.length > 0) {
      this.dispatchCallback('user-popup-messages', this.userPopupMessages)
    }
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

  protected getItemById(id: NavItemIdEnum): NavItem | NavLinkItem {
    const item = [...this.mainItems, ...this.userItems].find((item) => item.id === id)

    if (!item) {
      throw new Error(`NavItem with id "${id}" does not exist`)
    }

    return item
  }

  private init() {
    for (const item of this.mainItems.concat(this.userItems)) {
      this.itemBadge[item.id] = ref<MenuItemBadge | null>(null)

      if ('show_more' in item && item.show_more) {
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

    this.registerShortCut({ key: ['k'], alt: true }, () => {
      this.toggleKeyHints()
    })
    this.registerShortCut({ key: ['Escape'] }, () => {
      if (this.isAnyNavItemActive()) {
        this.close()
      }
    })
    this.registerShortCut({ key: ['ArrowDown'] }, () => {
      this.focusAdjacentEntry(1)
    })
    this.registerShortCut({ key: ['ArrowUp'] }, () => {
      this.focusAdjacentEntry(-1)
    })
    this.enableShortCuts()

    this.initPeriodicAjax()
  }

  private async updateBadgeValue(id: NavItemIdEnum, badge: NavItemBadge) {
    let success = true
    try {
      switch (badge.mode) {
        case 'num-pending-changes': {
          const res = (await this.api.get(badge.url)) as NumberOfPendingChangesResponse

          if (!res.number_of_pending_changes) {
            this.resetNavItemBadge(id)
          } else {
            this.setNavItemBadge(id, {
              content:
                res.number_of_pending_changes > 10
                  ? '9+'
                  : res.number_of_pending_changes.toString(),
              color: badge.color || 'default'
            })
          }
          break
        }
      }
    } catch {
      success = false
      this.setNavItemBadge(id, {
        content: '!',
        color: 'danger'
      })
    }

    if (badge.interval_in_seconds) {
      const timeout = setTimeout(
        () => {
          void this.updateBadgeValue(id, badge)
        },
        badge.interval_in_seconds * (success ? 1000 : 10000)
      )
      this.badgeUpdateTimeouts.set(id, timeout)
    }
  }

  public pauseBadgeUpdate(id: NavItemIdEnum) {
    const existing = this.badgeUpdateTimeouts.get(id)
    if (existing !== undefined) {
      clearTimeout(existing)
      this.badgeUpdateTimeouts.delete(id)
    }
  }

  public restartBadgeUpdate(id: NavItemIdEnum) {
    const existing = this.badgeUpdateTimeouts.get(id)
    if (existing !== undefined) {
      clearTimeout(existing)
      this.badgeUpdateTimeouts.delete(id)
    }
    const item = [...this.mainItems, ...this.userItems].find((item) => item.id === id)
    if (item?.badge) {
      void this.updateBadgeValue(id, item.badge)
    }
  }

  private initBadgeUpdate() {
    for (const item of this.mainItems.concat(this.userItems)) {
      if (item.badge) {
        void this.updateBadgeValue(item.id, item.badge)
      }
    }
  }

  private initPeriodicAjax() {
    void this.updateUserMessages()
    void this.updateUnacknowledgedIncompatibleWerks()
    void this.initBadgeUpdate()
  }
}
