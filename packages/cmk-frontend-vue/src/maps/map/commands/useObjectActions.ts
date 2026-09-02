/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type MaybeRefOrGetter, type Ref, reactive, ref, toValue } from 'vue'

import { useMapsApis, useStates, useToast } from '@/maps/services/context'
import type { DowntimeEntry, MapElement } from '@/maps/types/api'

interface DispatchOptions {
  hostFn: (hostname: string, siteId?: string | null) => Promise<void>
  serviceFn: (hostname: string, service: string, siteId?: string | null) => Promise<void>
  errorText: TranslatedString
  successText?: TranslatedString
}

export interface UseObjectActions {
  ackModalObject: Ref<MapElement | null>
  downtimeModalObject: Ref<MapElement | null>
  commentModalObject: Ref<MapElement | null>
  removeDowntimeModal: { visible: boolean; downtimes: DowntimeEntry[]; objectName: string }
  closeAckModal(): void
  closeDowntimeModal(): void
  closeRemoveDowntimeModal(): void
  handlers: {
    acknowledge(obj: MapElement | null): void
    removeAck(obj: MapElement | null): Promise<void>
    scheduleDowntime(obj: MapElement | null): void
    removeDowntime(obj: MapElement | null): Promise<void>
    addComment(obj: MapElement | null): void
    forceCheck(obj: MapElement | null): Promise<void>
    toggleNotifications(obj: MapElement | null, enable: boolean): Promise<void>
  }
}

/**
 * The commands an operator can send about one object, and the modals that ask
 * for what each of them needs.
 *
 * Every command splits the same way -- a host takes one call, a service takes
 * another -- and every surface that offers commands (the map view, the flow
 * map) needs the same seven. So the split, the modal state and the reporting
 * back live here once rather than per surface.
 */
export function useObjectActions(
  checkmkUrl: MaybeRefOrGetter<string | null | undefined>,
  onActionStart?: () => void
): UseObjectActions {
  const { _t } = usei18n()
  const toast = useToast()
  const { commands } = useMapsApis()
  const statesStore = useStates()

  const ackModalObject = ref<MapElement | null>(null)
  const downtimeModalObject = ref<MapElement | null>(null)
  const commentModalObject = ref<MapElement | null>(null)
  const removeDowntimeModal = reactive<{
    visible: boolean
    downtimes: DowntimeEntry[]
    objectName: string
  }>({ visible: false, downtimes: [], objectName: '' })

  function start(): string | null {
    onActionStart?.()
    const url = toValue(checkmkUrl)
    return url ?? null
  }

  async function dispatchHostOrService(
    obj: MapElement,
    { hostFn, serviceFn, errorText, successText }: DispatchOptions
  ): Promise<void> {
    try {
      // Prefer the live state-map site_id; fall back to a site_id carried
      // on the object itself (the Flow Map has no state-map entry but
      // tags its objects with the topology node's site).
      const siteId = statesStore.getState(obj.id)?.site_id ?? obj.site_id ?? null
      if (obj.type === 'service' && obj.host_name && obj.service_description) {
        await serviceFn(obj.host_name, obj.service_description, siteId)
      } else if (obj.host_name) {
        await hostFn(obj.host_name, siteId)
      } else {
        return
      }
      if (successText) {
        toast.success(successText)
      }
      statesStore.refreshAfterCommand()
    } catch (err) {
      const detail = err instanceof Error ? err.message : ''
      // Translated prefix + technical backend detail, joined by punctuation only.
      toast.error(detail ? untranslated(`${errorText}: ${detail}`) : errorText)
    }
  }

  function acknowledge(obj: MapElement | null): void {
    start()
    if (obj) {
      ackModalObject.value = obj
    }
  }

  async function removeAck(obj: MapElement | null): Promise<void> {
    start()
    if (!obj) {
      return
    }
    await dispatchHostOrService(obj, {
      // Checkmk finds the object's site for an acknowledgement by itself.
      hostFn: (hostname) => commands.removeAcknowledgementHost(hostname),
      serviceFn: (hostname, service) => commands.removeAcknowledgementService(hostname, service),
      errorText: _t('Failed to remove acknowledgement')
    })
  }

  function scheduleDowntime(obj: MapElement | null): void {
    start()
    if (obj) {
      downtimeModalObject.value = obj
    }
  }

  async function removeDowntime(obj: MapElement | null): Promise<void> {
    const url = start()
    if (!obj || !url) {
      return
    }
    let downtimes: DowntimeEntry[]
    try {
      if (obj.type === 'service' && obj.host_name && obj.service_description) {
        downtimes = await commands.listDowntimesService(url, obj.host_name, obj.service_description)
      } else if (obj.host_name) {
        downtimes = await commands.listDowntimesHost(url, obj.host_name)
      } else {
        return
      }
    } catch {
      toast.error(_t('Failed to remove downtime'))
      return
    }
    if (downtimes.length === 0) {
      toast.error(_t('No active downtimes found'))
      return
    }
    const single = downtimes.length === 1 ? downtimes[0] : undefined
    if (single !== undefined) {
      try {
        await commands.removeDowntimeById(url, single.id, single.site_id)
        toast.success(_t('Downtime removed'))
        statesStore.refreshAfterCommand()
      } catch {
        toast.error(_t('Failed to remove downtime'))
      }
      return
    }
    removeDowntimeModal.downtimes = downtimes
    removeDowntimeModal.objectName = obj.host_name ?? ''
    removeDowntimeModal.visible = true
  }

  function addComment(obj: MapElement | null): void {
    start()
    if (obj) {
      commentModalObject.value = obj
    }
  }

  async function forceCheck(obj: MapElement | null): Promise<void> {
    start()
    if (!obj) {
      return
    }
    await dispatchHostOrService(obj, {
      hostFn: commands.forceCheckHost,
      serviceFn: commands.forceCheckService,
      errorText: _t('Force check failed'),
      successText: _t('Force check scheduled')
    })
  }

  async function toggleNotifications(obj: MapElement | null, enable: boolean): Promise<void> {
    start()
    if (!obj) {
      return
    }
    await dispatchHostOrService(obj, {
      hostFn: enable ? commands.enableNotificationsHost : commands.disableNotificationsHost,
      serviceFn: enable
        ? commands.enableNotificationsService
        : commands.disableNotificationsService,
      errorText: _t('Failed to toggle notifications'),
      successText: _t('Notifications updated')
    })
  }

  // Modal close = command finished (or aborted) — refresh so the map
  // reflects the acknowledged/downtimed state without waiting a full tick.
  function closeAckModal(): void {
    ackModalObject.value = null
    statesStore.refreshAfterCommand()
  }

  function closeDowntimeModal(): void {
    downtimeModalObject.value = null
    statesStore.refreshAfterCommand()
  }

  function closeRemoveDowntimeModal(): void {
    removeDowntimeModal.visible = false
    statesStore.refreshAfterCommand()
  }

  return {
    ackModalObject,
    downtimeModalObject,
    commentModalObject,
    removeDowntimeModal,
    closeAckModal,
    closeDowntimeModal,
    closeRemoveDowntimeModal,
    handlers: {
      acknowledge,
      removeAck,
      scheduleDowntime,
      removeDowntime,
      addComment,
      forceCheck,
      toggleNotifications
    }
  }
}
