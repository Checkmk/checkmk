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
  type MapsTicket,
  type TicketApi,
  checkmkLoginUrl,
  checkmkLogoutUrl
} from '@/maps/api/ticket'
import type { UserRead } from '@/maps/types/api'

/** The ticket is short-lived (300 s); re-mint well before that so an idle map never 401s. */
const TICKET_REFRESH_INTERVAL_MS = 240_000

/**
 * What the first ticket is worth waiting for. Nothing can be shown without it,
 * and the re-mint interval above is far too slow to be the boot's retry -- a
 * restarting site would leave the operator on the loading screen for minutes.
 */
const BOOT_ATTEMPTS = 3
const BOOT_RETRY_MS = 2000

/**
 * The Checkmk session, as far as the SPA needs it.
 *
 * The one place that knows the daemon's credential scheme: it hands the daemon
 * transport an auth hook and nothing else in the SPA sees a ticket. That is
 * deliberate — the product ships several daemon-auth models today and this one is
 * expected to be replaced, at which point only this service and the hook change.
 */
export class MapsAuthService {
  private readonly ticket: Ref<MapsTicket | null> = ref(null)
  private refreshTimer: ReturnType<typeof setInterval> | null = null
  private initPromise: Promise<void> | null = null
  /**
   * The map the stream is bound to. Every mint scopes the ticket to it so the
   * daemon can key its shared broadcast loop by the map's real owner; null during
   * the list phase, before a map is opened.
   */
  private streamMap: string | null = null
  /** Set when the session is gone: the page is on its way to the login, so no retry. */
  private sessionLost = false
  private lastRefreshError: Error | null = null

  public readonly user: ComputedRef<UserRead | null>
  public readonly capabilities: ComputedRef<MapsCapabilities | null>
  public readonly isAdmin: ComputedRef<boolean>
  public readonly canConfigure: ComputedRef<boolean>
  public readonly canCreateMaps: ComputedRef<boolean>
  /** The reduced-capability credential the stream URL carries; see {@link MapsTicket}. */
  public readonly streamToken: ComputedRef<string | null>
  /**
   * Why the SPA could not start, once retrying is over. The app renders it
   * through its error boundary: a boot that will not complete is not a loading
   * state, and there is nothing else on screen to carry the reason.
   */
  public readonly bootError: Ref<Error | null> = ref(null)

  public constructor(private readonly api: Pick<TicketApi, 'fetchTicket'>) {
    this.capabilities = computed(() => this.ticket.value?.capabilities ?? null)
    this.user = computed(() => {
      const ticket = this.ticket.value
      if (!ticket) {
        return null
      }
      // Everything about the user comes from Checkmk: the SPA has no user model
      // of its own beyond what the ticket carries.
      return {
        user_id: ticket.user_id,
        is_admin: ticket.capabilities.configure,
        language: ticket.language || 'en',
        can_configure: ticket.capabilities.configure,
        can_create_maps: ticket.capabilities.may_edit,
        command_permissions: ticket.capabilities.commands
      }
    })
    this.isAdmin = computed(() => this.user.value?.is_admin ?? false)
    this.canConfigure = computed(() => this.user.value?.can_configure ?? false)
    this.canCreateMaps = computed(() => this.user.value?.can_create_maps ?? false)
    this.streamToken = computed(() => this.ticket.value?.stream_token ?? null)
  }

  /** The credential for a daemon request, in the shape the transport's hook wants. */
  public daemonHeaders(): Record<string, string> | undefined {
    const ticket = this.ticket.value
    return ticket ? { 'X-Maps-Ticket': ticket.ticket } : undefined
  }

  public mayCommand(verb: CommandVerb): boolean {
    return this.capabilities.value?.commands.includes(verb) ?? false
  }

  /**
   * Establishes the session once per SPA run and stays awaitable, so the first
   * navigation can be gated on a resolved session. ``streamMap`` seeds the scope
   * from the initial URL, so opening a map directly does not re-mint.
   */
  public init(streamMap?: string | null): Promise<void> {
    if (!this.initPromise) {
      if (streamMap !== undefined) {
        this.streamMap = streamMap
      }
      this.initPromise = this.boot()
    }
    return this.initPromise
  }

  /** The first ticket, retried over a blip and reported when it stays out. */
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

  /** Re-scopes the ticket to a map (or back to unbound) and mints it right away. */
  public async setStreamMap(name: string | null): Promise<void> {
    if (this.streamMap === name) {
      return
    }
    this.streamMap = name
    await this.refresh()
  }

  /**
   * Mints (or re-mints) the ticket from the surrounding Checkmk session. Returns
   * false and bounces to the Checkmk login when that session is gone.
   */
  public async refresh(): Promise<boolean> {
    try {
      this.ticket.value = await this.api.fetchTicket(this.streamMap ?? undefined)
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
        // A network blip, a daemon restart, a proxy 5xx: keep the ticket we have
        // (it may still be valid) and let the timer retry. Clearing here would
        // brick the SPA until a reload even though the session is fine.
        console.warn('[Maps] Failed to obtain ticket (will retry):', e)
        this.startRefreshTimer()
      }
      return false
    }
  }

  public logout(): void {
    this.dispose()
    window.location.assign(checkmkLogoutUrl())
  }

  /** Drops the session and stops the re-mint loop. */
  public dispose(): void {
    this.ticket.value = null
    this.initPromise = null
    this.streamMap = null
    if (this.refreshTimer !== null) {
      clearInterval(this.refreshTimer)
      this.refreshTimer = null
    }
  }

  private startRefreshTimer(): void {
    if (this.refreshTimer === null) {
      this.refreshTimer = setInterval(() => void this.refresh(), TICKET_REFRESH_INTERVAL_MS)
    }
  }
}
