<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Acknowledge, or schedule downtime for, every host in a SETUP folder -- the
folder-scoped action a NOC reaches for most: a rack, a rollout, a site going
down for maintenance.

A folder is not a Checkmk host group, so there is no single command for it; each
host is commanded in turn, a few at a time. A live count of what the command
will reach, and a recursion toggle that changes it, is what keeps that from
being fired blind.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, computed, ref } from 'vue'

import CommandFeedback from '@/maps/map/commands/CommandFeedback.vue'
import { messageOf } from '@/maps/map/commands/commandErrors'
import {
  acknowledgeOptions,
  childHostTargets,
  useCommandForms
} from '@/maps/map/commands/commandForms'
import { useBulkCommandSubmit } from '@/maps/map/commands/useBulkCommandSubmit'
import { useAuth, useMapsApis } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { CommandTarget, FolderTreeNode } from '@/maps/types/api'
import { isProblemState } from '@/maps/utils/problemState'
import type { ScheduleDowntimeOptions } from '@/monitoring/shared/api/actions/downtime'
import AcknowledgeForm, {
  type AcknowledgeValues
} from '@/monitoring/shared/components/action/actions/AcknowledgeForm.vue'
import ScheduleDowntimeForm, {
  type ScheduleDowntimeFormValues
} from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'
import { noDowntimeWindow } from '@/monitoring/shared/components/action/actions/scheduleDowntime'

import { folderHosts } from '../objects'

export type FolderBulkMode = 'acknowledge' | 'downtime'

const props = defineProps<{
  folder: FolderTreeNode
  initialMode?: FolderBulkMode | undefined
}>()
const emit = defineEmits<{ close: [] }>()

const { _t, _tn } = usei18n()
const { commands } = useMapsApis()
const auth = useAuth()

const canAcknowledge = computed(() => auth.mayCommand('acknowledge'))
const canDowntime = computed(() => auth.mayCommand('schedule_downtime'))

const mode = ref<FolderBulkMode>(
  props.initialMode ?? (canDowntime.value ? 'downtime' : 'acknowledge')
)
const modes = computed(() => [
  ...(canAcknowledge.value ? [{ label: _t('Acknowledge'), value: 'acknowledge' }] : []),
  ...(canDowntime.value ? [{ label: _t('Schedule downtime'), value: 'downtime' }] : [])
])

const recursive = ref(true)
const forms = useCommandForms()
const ackDraft = ref(forms.acknowledgeValues()) as Ref<AcknowledgeValues>
const downtimeDraft = ref(forms.downtimeValues()) as Ref<ScheduleDowntimeFormValues>
const valid = ref(false)
const children = ref<CommandTarget[]>([])
// Resolved once per submit, so every host gets the same window.
let downtime: ScheduleDowntimeOptions | null = null

const hosts = computed(() => folderHosts(props.folder, recursive.value))
// Only offered where it changes something.
const hasSubfolders = computed(() => props.folder.children.some(({ kind }) => kind === 'folder'))
// Checkmk refuses to acknowledge a host that has no problem, and a tile that is
// red for a failing service belongs to a host that may well be UP.
const targets = computed<CommandTarget[]>(() =>
  hosts.value
    .filter(({ state }) => mode.value === 'downtime' || isProblemState(state))
    .map(({ host, site }) => ({ host, service: null, site }))
)
const skipped = computed(() => hosts.value.length - targets.value.length)
// Only service problems: "Acknowledge 0 hosts" would be a dead button.
const nothingToAcknowledge = computed(
  () => mode.value === 'acknowledge' && hosts.value.length > 0 && targets.value.length === 0
)

const { submitting, progress, succeeded, pending, error, blocked, submit, reject } =
  useBulkCommandSubmit({
    what: 'folder-bulk-command',
    targets: () => [...targets.value, ...children.value],
    onDone: () => emit('close'),
    send: (target) =>
      mode.value === 'acknowledge'
        ? commands.acknowledgeHost(target.host, acknowledgeOptions(ackDraft.value))
        : commands.downtimeHost(target.host, downtime!)
  })

async function onSubmit(): Promise<void> {
  if (!valid.value || blocked.value || pending.value === 0) {
    return
  }
  children.value = []
  if (mode.value === 'downtime') {
    downtime = forms.downtimeOptions(downtimeDraft.value)
    if (downtime === null) {
      reject(noDowntimeWindow().message)
      return
    }
    // Looked up before the first run only: a retry is about what refused.
    if (downtimeDraft.value.includeChildHosts && progress.value === 0) {
      try {
        children.value = await childHostTargets(commands, targets.value)
      } catch (caught) {
        reject(messageOf(caught, _t('Could not find the child hosts')))
        return
      }
    }
  }
  await submit()
}
</script>

<template>
  <MapsModal
    :open="true"
    :title="_t('Folder actions — %{folder}', { folder: folder.title })"
    :scrolls="false"
    closable
    @close="emit('close')"
  >
    <CmkToggleButtonGroup v-if="modes.length > 1" v-model="mode" :options="modes" spacing="none" />

    <CmkAlert
      v-if="nothingToAcknowledge"
      class="maps-folder-bulk-action-modal__nothing"
      variant="info"
      :text="
        hasSubfolders && !recursive
          ? _t(
              'No host directly in “%{folder}” is down or unreachable. Include sub-folders to reach the hosts below it.',
              { folder: folder.title }
            )
          : _t(
              'No host in “%{folder}” is down or unreachable. A host that is up and red is red for its services: acknowledge those on the host.',
              { folder: folder.title }
            )
      "
    />
    <p v-else class="maps-folder-bulk-action-modal__subtitle">
      {{
        _tn(
          'Applies to %{count} host in “%{folder}”.',
          'Applies to %{count} hosts in “%{folder}”.',
          targets.length,
          { count: targets.length, folder: folder.title }
        )
      }}
    </p>
    <p v-if="skipped && !nothingToAcknowledge" class="maps-folder-bulk-action-modal__skipped">
      {{
        _tn('%{count} host that is up left out.', '%{count} hosts that are up left out.', skipped, {
          count: skipped
        })
      }}
    </p>
    <CmkCheckbox v-if="hasSubfolders" v-model="recursive" :label="_t('Include sub-folders')" />

    <template v-if="!nothingToAcknowledge">
      <AcknowledgeForm
        v-if="mode === 'acknowledge'"
        v-model="ackDraft"
        class="maps-folder-bulk-action-modal__form"
        v-bind="forms.acknowledgeProps('host')"
        @update:valid="valid = $event"
      />
      <ScheduleDowntimeForm
        v-else
        v-model="downtimeDraft"
        class="maps-folder-bulk-action-modal__form"
        v-bind="forms.downtimeProps('host')"
        @update:valid="valid = $event"
      />
    </template>

    <CommandFeedback
      :error="error"
      :succeeded="succeeded > 0"
      :succeeded-text="
        _tn('%{count} host done.', '%{count} hosts done.', succeeded, { count: succeeded })
      "
    />

    <template #footer>
      <CmkButton variant="secondary" @click="emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton
        v-if="!nothingToAcknowledge"
        variant="primary"
        :disabled="blocked || !valid || pending === 0"
        @click="onSubmit"
      >
        {{
          submitting
            ? _t('Sending %{current}/%{total}…', { current: progress, total: pending })
            : mode === 'acknowledge'
              ? _tn('Acknowledge %{count} host', 'Acknowledge %{count} hosts', pending, {
                  count: pending
                })
              : _tn('Downtime %{count} host', 'Downtime %{count} hosts', pending, {
                  count: pending
                })
        }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-folder-bulk-action-modal__subtitle {
  margin: var(--dimension-4) 0 var(--dimension-3);
  font-size: var(--font-size-normal);
  color: var(--font-color);
}

/* No wider than the dialog's own minimum, so switching between the two modes
   does not resize the dialog around it. */
.maps-folder-bulk-action-modal__nothing {
  box-sizing: border-box;
  max-width: 450px;
  margin: var(--dimension-4) 0 var(--dimension-3);
}

.maps-folder-bulk-action-modal__skipped {
  margin: 0 0 var(--dimension-3);
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

/* A fixed width, so switching between the two forms, or opening the downtime
   form's advanced options, does not resize the dialog around them. */
.maps-folder-bulk-action-modal__form {
  width: min(520px, 80vw);
  margin-top: var(--dimension-5);
}
</style>
