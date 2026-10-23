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
  NavLinkItem,
  NavToggleItem
} from 'cmk-shared-typing/typescript/main_menu'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { type KeyShortcut, KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { ServiceBase } from 'cmk-ui-library/lib/service/base'
import { type Ref, ref } from 'vue'

import {
  isAnyCheatSheetVisible,
  subscribeAnyCheatSheetVisible
} from '@/lib/keyboard-cheat-sheet/cheatSheetKey'

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
  UserMessagesResult,
  UserPopupMessageRef
} from './type-defs'

const { _t } = usei18n()

export class MainMenuService extends ServiceBase {
  public currentItem: Ref<NavItem | null> = ref<NavItem | null>(null)
  /** Shown together with the keyboard cheat sheet, of this frame or the content frame. */
  public showKeyHints: Ref<boolean> = ref<boolean>(isAnyCheatSheetVisible())
  protected showAllTopic = ref<{ id: string; topic: NavItemTopic } | null>(null)
  protected showMoreActive: { [key: string]: Ref<boolean> } = {}
  protected userMessageTrigger: Ref<UserHintMessages | null> = ref<UserHintMessages | null>(null)
  protected unackIncompWerksTrigger: Ref<UnackIncompWerksResult | null> =
    ref<UnackIncompWerksResult | null>(null)
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
    subscribeAnyCheatSheetVisible((visible) => {
      this.showKeyHints.value = visible
    })
    this.init()
  }

  public getNavShortCutInfo(shortcut: NavItemShortcut): string {
    return KeyShortcutService.getShortCutInfo(this.toKeyShortcut(shortcut))
  }

  public getNavShortCutCombo(shortcut: NavItemShortcut): string[] {
    return KeyShortcutService.getShortCutCombo(this.toKeyShortcut(shortcut))
  }

  public registerToggleShortcut(item: NavToggleItem, toggle: () => void): () => void {
    const id = this.shortCutService.on(
      {
        ...this.toKeyShortcut(item.shortcut),
        preventDefault: item.shortcut.prevent_default || false,
        scope: _t('Main menu'),
        description: untranslated(item.title)
      },
      toggle
    )
    return () => this.shortCutService.remove([id])
  }

  private toKeyShortcut(shortcut: NavItemShortcut): KeyShortcut {
    return {
      key: [shortcut.key],
      alt: shortcut.alt,
      ctrl: shortcut.ctrl,
      shift: shortcut.shift
    }
  }

  public isAnyNavItemActive() {
    return this.currentItem.value !== null
  }

  public isNavItemActive(id: NavItemIdEnum) {
    return this.currentItem.value?.id === id
  }

  public navigate(id: NavItemIdEnum) {
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
        if (this.unackIncompWerksTrigger.value && this.unackIncompWerksTrigger.value.count > 0) {
          return this.unackIncompWerksTrigger.value.text
        }
        return null
      default:
        return null
    }
  }

  public chipEntry(mode: ChipModeEnum): string | null {
    switch (mode) {
      case 'user-messages-hint':
        if (this.userMessageTrigger.value && this.userMessageTrigger.value.count > 0) {
          return `${this.userMessageTrigger.value.count} ${this.userMessageTrigger.value.text}`
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
    let res: UserMessagesResult
    try {
      res = await this.api.getUserMessages()
    } catch (error) {
      console.error('Could not load the user messages', error)
      this.resetNavItemBadge('user')
      return
    }

    this.userMessageTrigger.value = res.hint_messages
    if (this.userMessageTrigger.value.count > 0) {
      this.setNavItemBadge('user', {
        content: this.userMessageTrigger.value.count.toString(),
        color: 'danger'
      })
    } else {
      this.resetNavItemBadge('user')
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
    try {
      this.unackIncompWerksTrigger.value = await this.api.getUnacknowledgedIncompatibleWerks()
    } catch (error) {
      console.error('Could not load the unacknowledged incompatible werks', error)
      this.resetNavItemBadge('help')
      return
    }

    if (this.unackIncompWerksTrigger.value.count === 0) {
      this.setNavItemBadge('help', null)
    } else {
      this.setNavItemBadge('help', {
        color: 'danger',
        content: this.unackIncompWerksTrigger.value.count.toString()
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
            shift: item.shortcut.shift || false,
            preventDefault: item.shortcut.prevent_default || false,
            scope: _t('Main menu'),
            description: untranslated(item.title)
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

    const scope = _t('Main menu')
    this.registerShortCut({ key: ['Escape'], scope, description: _t('Close menu') }, () => {
      if (this.isAnyNavItemActive()) {
        this.close()
      }
    })
    this.registerShortCut({ key: ['ArrowDown'], scope, description: _t('Next entry') }, () => {
      this.focusAdjacentEntry(1)
    })
    this.registerShortCut({ key: ['ArrowUp'], scope, description: _t('Previous entry') }, () => {
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
