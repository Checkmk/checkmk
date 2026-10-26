/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The commands the slide-in offers about the one object it shows.
 *
 * The forms are the monitoring pages' own, so acknowledging from a map asks
 * what acknowledging from the host view asks. Sending stays here: a map object
 * may be a whole group, and a group goes to its own connection's site. The
 * shared action factories are not used because they replace Checkmk's answer
 * with a generic one, and a rejected group command needs the reason.
 */
import { getLocalTimeZone, now } from '@internationalized/date'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type ComputedRef, type Ref, computed, reactive, ref, watch } from 'vue'

import { useMapsApis, useStates, useToast } from '@/maps/services/context'
import type { MapElement, ObjectState } from '@/maps/types/api'
import type { ScheduleDowntimeOptions } from '@/monitoring/shared/api/actions/downtime'
import type { ActionFeedback } from '@/monitoring/shared/components/action/ActionFeedback.vue'
import AcknowledgeForm, {
  type AcknowledgeValues
} from '@/monitoring/shared/components/action/actions/AcknowledgeForm.vue'
import CommentForm, {
  type CommentValues
} from '@/monitoring/shared/components/action/actions/CommentForm.vue'
import ScheduleDowntimeForm, {
  type ScheduleDowntimeFormValues,
  defaultScheduleDowntimeValues
} from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'
import {
  ACK_ACTION_ID,
  acknowledgeDefaults
} from '@/monitoring/shared/components/action/actions/acknowledge'
import { COMMENT_ACTION_ID } from '@/monitoring/shared/components/action/actions/comment'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import {
  SCHEDULE_DOWNTIME_ACTION_ID,
  downtimePresets,
  noDowntimeWindow,
  scheduleDowntimeOptions
} from '@/monitoring/shared/components/action/actions/scheduleDowntime'
import {
  type MonitoringActionRegistry,
  createActionRegistry
} from '@/monitoring/shared/components/action/registry'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

import { describeGroupCommandError, messageOf } from './commandErrors'
import { useMapsCommandSettings } from './commandSettings'

export const OBJECT_ACTION_IDS = {
  acknowledge: ACK_ACTION_ID,
  removeAcknowledgement: 'remove_acknowledgments',
  scheduleDowntime: SCHEDULE_DOWNTIME_ACTION_ID,
  removeDowntimes: 'remove_downtimes',
  forceCheck: RESCHEDULE_ACTION_ID,
  comment: COMMENT_ACTION_ID,
  enableNotifications: 'enable_notifications',
  disableNotifications: 'disable_notifications'
} as const

/** What a command is about, as Checkmk addresses it. */
type CommandScope =
  | { kind: 'host'; host: string }
  | { kind: 'service'; host: string; service: string }
  | { kind: 'hostgroup' | 'servicegroup'; group: string }

type GroupScope = Extract<CommandScope, { group: string }>

function isGroupScope(scope: CommandScope): scope is GroupScope {
  return scope.kind === 'hostgroup' || scope.kind === 'servicegroup'
}

function scopeOf(object: MapElement): CommandScope | null {
  // A site's host name is the site, and an aggregation has no host or service
  // of its own: neither takes a command.
  if (object.type === 'site' || object.type === 'aggregation') {
    return null
  }
  if ((object.type === 'hostgroup' || object.type === 'servicegroup') && object.group_name) {
    return { kind: object.type, group: object.group_name }
  }
  if (object.type === 'service') {
    return object.host_name && object.service_description
      ? { kind: 'service', host: object.host_name, service: object.service_description }
      : null
  }
  return object.host_name ? { kind: 'host', host: object.host_name } : null
}

export interface ObjectActionsOptions {
  object: () => MapElement | null
  state: () => ObjectState | undefined
  checkmkUrl: () => string | null | undefined
}

export interface ObjectActions {
  /** Whether the object takes commands at all, and whether as a group. */
  scope: ComputedRef<'single' | 'group' | null>
  /** The action whose form is open. */
  activeAction: ComputedRef<MonitoringAction<unknown, MapElement> | null>
  /** Whether removing the object's downtimes waits for a confirmation. */
  confirmingRemoveDowntimes: Ref<boolean>
  /** How the last command went, shown by the actions as in the host view. */
  feedback: Ref<ActionFeedback | null>
  feedbackOpen: Ref<boolean>
  /** Whether an action's command is still on its way. */
  running: (actionId: string) => boolean
  /** Opens an action's form, or sends a command that needs none. */
  select: (actionId: string) => void
  /** Sends the open form; a failure is returned to show beside it. */
  submit: (values: unknown) => Promise<ActionFeedback | null>
  confirmRemoveDowntimes: () => Promise<void>
  close: () => void
}

export function useObjectActions(options: ObjectActionsOptions): ObjectActions {
  const { _t } = usei18n()
  const { commands } = useMapsApis()
  const statesStore = useStates()
  const toast = useToast()
  const settings = useMapsCommandSettings()
  const ackDefaults = acknowledgeDefaults(settings.acknowledge_defaults)
  const presets = downtimePresets(settings.downtime_presets)

  const commandScope = computed(() => {
    const object = options.object()
    return object ? scopeOf(object) : null
  })

  const activeActionId = ref<string | null>(null)
  const confirmingRemoveDowntimes = ref(false)
  const feedback = ref<ActionFeedback | null>(null)
  const feedbackOpen = ref(false)
  // A command already on its way is not sent twice by a second click. Keyed by
  // object too, so the next object's button is not held up by it.
  const sending = reactive(new Set<string>())
  function sendingKey(objectId: string, actionId: string): string {
    return `${objectId}/${actionId}`
  }

  function close(): void {
    activeActionId.value = null
    confirmingRemoveDowntimes.value = false
  }

  // A dialog opened for one object must not send its command to the next, nor
  // its result read as the next object's.
  watch(
    () => options.object()?.id,
    () => {
      close()
      feedback.value = null
    }
  )

  function groupLabel(scope: GroupScope): TranslatedString {
    return scope.kind === 'hostgroup' ? _t('host group') : _t('service group')
  }

  function siteId(): string | null {
    return options.state()?.site_id ?? options.object()?.site_id ?? null
  }

  function checkmkUrl(): string | null {
    return options.checkmkUrl() ?? null
  }

  async function run(
    scope: CommandScope,
    send: () => Promise<void>,
    success: TranslatedString,
    heading: TranslatedString
  ): Promise<ActionFeedback> {
    try {
      await send()
    } catch (caught) {
      const message = isGroupScope(scope)
        ? describeGroupCommandError(messageOf(caught, heading), true, groupLabel(scope), _t)
        : messageOf(caught, heading)
      return { variant: 'error', heading, message }
    }
    statesStore.refreshAfterCommand()
    return { variant: 'success', message: success }
  }

  function buildRegistry(scope: CommandScope): MonitoringActionRegistry<MapElement> {
    const targetKind =
      scope.kind === 'service' || scope.kind === 'servicegroup' ? 'service' : 'host'
    const groupHint = isGroupScope(scope)
      ? {
          description: [_t('Applies to every member of the %{type}.', { type: groupLabel(scope) })]
        }
      : {}

    const acknowledge: MonitoringAction<AcknowledgeValues, MapElement> = {
      id: OBJECT_ACTION_IDS.acknowledge,
      title: _t('Acknowledge problem'),
      submitLabel: _t('Acknowledge'),
      ...groupHint,
      form: AcknowledgeForm,
      formProps: {
        targetKind,
        presetsUrl: settings.acknowledge_presets_url,
        notificationRulesUrl: settings.notification_rules_url
      },
      defaultValues: () => ({
        comment: '',
        expireOnEnabled: false,
        expireOn: now(getLocalTimeZone()).add({ seconds: ackDefaults.expireSeconds }),
        sticky: ackDefaults.sticky,
        persistent: ackDefaults.persistent,
        notify: ackDefaults.notify
      }),
      perform: (_targets, values) => {
        const ack = {
          comment: values.comment,
          sticky: values.sticky,
          notify: values.notify,
          persistent: values.persistent,
          ...(values.expireOnEnabled && values.expireOn
            ? { expire_on: values.expireOn.toDate().toISOString() }
            : {})
        }
        return run(
          scope,
          () => {
            switch (scope.kind) {
              case 'hostgroup':
                return commands.acknowledgeHostgroup(checkmkUrl(), scope.group, ack)
              case 'servicegroup':
                return commands.acknowledgeServicegroup(checkmkUrl(), scope.group, ack)
              case 'service':
                return commands.acknowledgeService(scope.host, scope.service, ack)
              case 'host':
                return commands.acknowledgeHost(scope.host, ack)
            }
          },
          _t('Acknowledgement set'),
          _t('Could not acknowledge the problem')
        )
      }
    }

    // Child hosts go in the same request as the object, so a failure leaves
    // nothing scheduled and a retry cannot double the downtime.
    function sendDowntime(downtime: ScheduleDowntimeOptions, children: string[]): Promise<void> {
      switch (scope.kind) {
        case 'hostgroup':
          return commands.downtimeHostgroup(checkmkUrl(), scope.group, downtime, children)
        case 'servicegroup':
          return commands.downtimeServicegroup(checkmkUrl(), scope.group, downtime)
        case 'service':
          return commands.downtimeService(scope.host, scope.service, downtime)
        case 'host':
          return children.length
            ? commands.downtimeHosts(null, [scope.host, ...children], downtime)
            : commands.downtimeHost(scope.host, downtime)
      }
    }

    // The form offers child hosts only where the target is hosts. They are
    // looked up where the parents are monitored. A group's parents are asked
    // from the site: the slide-in's member list may still be loading, have
    // failed, or leave out excluded members the downtime still covers.
    async function childHosts(): Promise<string[]> {
      if (scope.kind === 'host') {
        return commands.childHosts(null, [scope.host])
      }
      if (scope.kind !== 'hostgroup') {
        return []
      }
      const parents = await commands.hostgroupHosts(checkmkUrl(), scope.group)
      return commands.childHosts(checkmkUrl(), parents)
    }

    const scheduleDowntime: MonitoringAction<ScheduleDowntimeFormValues, MapElement> = {
      id: OBJECT_ACTION_IDS.scheduleDowntime,
      title: _t('Schedule downtime'),
      submitLabel: _t('Schedule downtime'),
      ...groupHint,
      form: ScheduleDowntimeForm,
      formProps: {
        targetKind,
        recurrences: settings.downtime_recurrences,
        presets,
        presetsUrl: settings.downtime_presets_url
      },
      defaultValues: () => defaultScheduleDowntimeValues(presets),
      perform: async (_targets, values) => {
        const downtime = scheduleDowntimeOptions(values, presets)
        if (downtime === null) {
          return noDowntimeWindow()
        }
        return run(
          scope,
          async () => sendDowntime(downtime, values.includeChildHosts ? await childHosts() : []),
          _t('Downtime scheduled'),
          _t('Could not schedule the downtime')
        )
      }
    }

    if (isGroupScope(scope)) {
      return createActionRegistry<MapElement>([acknowledge, scheduleDowntime])
    }

    const { host } = scope
    const service = scope.kind === 'service' ? scope.service : null

    const comment: MonitoringAction<CommentValues, MapElement> = {
      id: OBJECT_ACTION_IDS.comment,
      title: _t('Add comment'),
      submitLabel: _t('Add comment'),
      form: CommentForm,
      defaultValues: () => ({ comment: '' }),
      perform: (_targets, values) =>
        run(
          scope,
          () =>
            service === null
              ? commands.addCommentHost(host, values.comment)
              : commands.addCommentService(host, service, values.comment),
          _t('Comment added'),
          _t('Could not add the comment')
        )
    }

    function immediate(
      id: string,
      title: TranslatedString,
      send: () => Promise<void>,
      success: TranslatedString,
      heading: TranslatedString
    ): MonitoringAction<undefined, MapElement> {
      return {
        id,
        title,
        submitLabel: title,
        defaultValues: () => undefined,
        perform: () => run(scope, send, success, heading)
      }
    }

    return createActionRegistry<MapElement>([
      acknowledge,
      scheduleDowntime,
      comment,
      immediate(
        OBJECT_ACTION_IDS.removeAcknowledgement,
        _t('Remove acknowledgement'),
        () =>
          service === null
            ? commands.removeAcknowledgementHost(host)
            : commands.removeAcknowledgementService(host, service),
        _t('Acknowledgement removed'),
        _t('Could not remove the acknowledgement')
      ),
      immediate(
        OBJECT_ACTION_IDS.removeDowntimes,
        _t('Remove downtimes'),
        () =>
          service === null
            ? commands.removeDowntimeHost(checkmkUrl(), host)
            : commands.removeDowntimeService(checkmkUrl(), host, service),
        _t('Downtimes removed'),
        _t('Could not remove the downtimes')
      ),
      immediate(
        OBJECT_ACTION_IDS.forceCheck,
        _t('Force check'),
        () =>
          service === null
            ? commands.forceCheckHost(host, siteId())
            : commands.forceCheckService(host, service, siteId()),
        _t('Force check scheduled'),
        _t('Could not schedule the check')
      ),
      immediate(
        OBJECT_ACTION_IDS.enableNotifications,
        _t('Enable notifications'),
        () =>
          service === null
            ? commands.enableNotificationsHost(host, siteId())
            : commands.enableNotificationsService(host, service, siteId()),
        _t('Notifications enabled'),
        _t('Could not enable notifications')
      ),
      immediate(
        OBJECT_ACTION_IDS.disableNotifications,
        _t('Disable notifications'),
        () =>
          service === null
            ? commands.disableNotificationsHost(host, siteId())
            : commands.disableNotificationsService(host, service, siteId()),
        _t('Notifications disabled'),
        _t('Could not disable notifications')
      )
    ])
  }

  const registry = computed<MonitoringActionRegistry<MapElement>>(() =>
    commandScope.value ? buildRegistry(commandScope.value) : {}
  )

  // A result is shown where it was asked for. Once the slide-in has moved on to
  // another object or closed, that place is gone, and only a toast still
  // reaches the operator.
  function report(result: ActionFeedback, objectId: string): void {
    if (options.object()?.id === objectId) {
      feedback.value = result
      feedbackOpen.value = true
    } else if (result.variant === 'success') {
      toast.success(result.message)
    } else {
      const { heading, message } = result
      toast.error(heading && heading !== message ? untranslated(`${heading}: ${message}`) : message)
    }
  }

  /**
   * Sends an action's command and shows how it went. A refusal of an open form
   * is returned instead, for its dialog to show; a success closes the dialog.
   */
  async function perform(actionId: string, values: unknown): Promise<ActionFeedback | null> {
    const action = registry.value[actionId]
    const object = options.object()
    if (!action || !object) {
      return null
    }
    const key = sendingKey(object.id, actionId)
    if (sending.has(key)) {
      return null
    }
    sending.add(key)
    feedback.value = null
    let result: ActionFeedback
    try {
      result = await action.perform([object], values)
    } finally {
      sending.delete(key)
    }
    // Another object, or another dialog, may have taken over meanwhile.
    const dialogOpen = activeActionId.value === actionId && options.object()?.id === object.id
    if (dialogOpen && result.variant === 'error') {
      return result
    }
    if (dialogOpen) {
      activeActionId.value = null
    }
    report(result, object.id)
    return null
  }

  function select(actionId: string): void {
    const action = registry.value[actionId]
    if (!action) {
      return
    }
    if (action.form) {
      activeActionId.value = actionId
    } else if (actionId === OBJECT_ACTION_IDS.removeDowntimes) {
      confirmingRemoveDowntimes.value = true
    } else {
      void perform(actionId, undefined)
    }
  }

  async function submit(values: unknown): Promise<ActionFeedback | null> {
    return activeActionId.value === null ? null : perform(activeActionId.value, values)
  }

  async function confirmRemoveDowntimes(): Promise<void> {
    confirmingRemoveDowntimes.value = false
    await perform(OBJECT_ACTION_IDS.removeDowntimes, undefined)
  }

  return {
    scope: computed(() =>
      commandScope.value ? (isGroupScope(commandScope.value) ? 'group' : 'single') : null
    ),
    activeAction: computed(() =>
      activeActionId.value === null ? null : (registry.value[activeActionId.value] ?? null)
    ),
    confirmingRemoveDowntimes,
    feedback,
    feedbackOpen,
    running: (actionId) => {
      const object = options.object()
      return object !== null && sending.has(sendingKey(object.id, actionId))
    },
    select,
    submit,
    confirmRemoveDowntimes,
    close
  }
}
