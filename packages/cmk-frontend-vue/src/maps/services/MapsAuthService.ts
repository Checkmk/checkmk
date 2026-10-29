/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { type ComputedRef, type Ref, computed, ref } from 'vue'

import {
  type CommandVerb,
  type MapsCapabilities,
  type MapsSession,
  type SessionApi,
  checkmkLoginUrl,
  checkmkLogoutUrl
} from '@/maps/api/session'
import type { UserRead } from '@/maps/types/api'

/**
 * The daemon checks the session without counting it as activity, so an open map
 * fetches it now and then: the GUI idle timeout must not end the session of a
 * user who watches a map, and a changed permission shows without a reload.
 */
const SESSION_REFRESH_INTERVAL_MS = 240_000

/**
 * What the session is worth waiting for. Nothing can be shown without it, so a
 * restarting site must not leave the operator on the loading screen for good.
 */
const BOOT_ATTEMPTS = 3
const BOOT_RETRY_MS = 2000

/**
 * The Checkmk session, as far as the SPA needs it.
 *
 * The daemon authenticates the same session from the cookie the browser sends,
 * so nothing here is a credential: it is who is logged in and what the SPA may
 * offer them.
 */
export class MapsAuthService {
  private readonly session: Ref<MapsSession | null> = ref(null)
  private initPromise: Promise<void> | null = null
  /** Set when the session is gone: the page is on its way to the login, so no retry. */
  private sessionLost = false
  private lastRefreshError: Error | null = null
  private refreshTimer: ReturnType<typeof setInterval> | null = null

  public readonly user: ComputedRef<UserRead | null>
  public readonly capabilities: ComputedRef<MapsCapabilities | null>
  public readonly isAdmin: ComputedRef<boolean>
  public readonly canConfigure: ComputedRef<boolean>
  public readonly canCreateMaps: ComputedRef<boolean>
  /**
   * Why the SPA could not start, once retrying is over. The app renders it
   * through its error boundary: a boot that will not complete is not a loading
   * state, and there is nothing else on screen to carry the reason.
   */
  public readonly bootError: Ref<Error | null> = ref(null)

  public constructor(private readonly api: Pick<SessionApi, 'fetchSession'>) {
    this.capabilities = computed(() => this.session.value?.capabilities ?? null)
    this.user = computed(() => {
      const session = this.session.value
      if (!session) {
        return null
      }
      // Everything about the user comes from Checkmk: the SPA has no user model
      // of its own beyond what the session carries.
      return {
        user_id: session.user_id,
        is_admin: session.capabilities.configure,
        language: session.language || 'en',
        can_configure: session.capabilities.configure,
        can_create_maps: session.capabilities.may_edit,
        command_permissions: session.capabilities.commands
      }
    })
    this.isAdmin = computed(() => this.user.value?.is_admin ?? false)
    this.canConfigure = computed(() => this.user.value?.can_configure ?? false)
    this.canCreateMaps = computed(() => this.user.value?.can_create_maps ?? false)
  }

  public mayCommand(verb: CommandVerb): boolean {
    return this.capabilities.value?.commands.includes(verb) ?? false
  }

  /**
   * Establishes the session once per SPA run and stays awaitable, so the first
   * navigation can be gated on a resolved session.
   */
  public init(): Promise<void> {
    if (!this.initPromise) {
      this.initPromise = this.boot()
    }
    return this.initPromise
  }

  private async boot(): Promise<void> {
    let lastError: Error | null = null
    for (let attempt = 1; attempt <= BOOT_ATTEMPTS; attempt += 1) {
      if (await this.refresh()) {
        return
      }
      if (this.sessionLost) {
        return
      }
      lastError = this.lastRefreshError
      if (attempt < BOOT_ATTEMPTS) {
        await new Promise((resolve) => setTimeout(resolve, BOOT_RETRY_MS))
      }
    }
    this.bootError.value =
      lastError ?? new Error('Maps could not establish a session with the Checkmk site.')
  }

  /**
   * Fetches the session again. Returns false and bounces to the Checkmk login
   * when that session is gone.
   */
  public async refresh(): Promise<boolean> {
    try {
      this.session.value = await this.api.fetchSession()
      this.lastRefreshError = null
      this.bootError.value = null
      this.startRefreshTimer()
      return true
    } catch (e: unknown) {
      this.lastRefreshError = e instanceof Error ? e : new Error(String(e))
      if (e instanceof CmkApiError && (e.statusCode === 401 || e.statusCode === 403)) {
        // No Checkmk session behind the SPA any more — hand off to the GUI login.
        this.sessionLost = true
        this.dispose()
        window.location.assign(checkmkLoginUrl())
      } else {
        // A network blip, a site restart, a proxy 5xx: keep the session we have
        // and let the timer retry, clearing it would brick the SPA until a reload.
        console.warn('[Maps] Failed to fetch the session:', e)
        this.startRefreshTimer()
      }
      return false
    }
  }

  public logout(): void {
    this.dispose()
    window.location.assign(checkmkLogoutUrl())
  }

  public dispose(): void {
    this.session.value = null
    this.initPromise = null
    if (this.refreshTimer !== null) {
      clearInterval(this.refreshTimer)
      this.refreshTimer = null
    }
  }

  private startRefreshTimer(): void {
    this.refreshTimer ??= setInterval(() => void this.refresh(), SESSION_REFRESH_INTERVAL_MS)
  }
}
