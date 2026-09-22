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
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import CmkTimeRangePicker from 'cmk-ui-library/components/date-time/CmkTimeRangePicker.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import CommandFeedback from '@/maps/map/commands/CommandFeedback.vue'
import { useBulkCommandSubmit } from '@/maps/map/commands/useBulkCommandSubmit'
import { useDowntimeWindow } from '@/maps/map/commands/useDowntimeWindow'
import { useAuth, useMapsApis } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { CommandTarget, FolderTreeNode } from '@/maps/types/api'
import { isProblemState } from '@/maps/utils/problemState'

import { folderHosts } from '../objects'

const props = defineProps<{ folder: FolderTreeNode }>()
const emit = defineEmits<{ close: [] }>()

const { _t, _tn } = usei18n()
const { commands } = useMapsApis()
const auth = useAuth()

const canAcknowledge = computed(() => auth.mayCommand('acknowledge'))
const canDowntime = computed(() => auth.mayCommand('schedule_downtime'))

const mode = ref<'acknowledge' | 'downtime'>(canDowntime.value ? 'downtime' : 'acknowledge')
const modes = computed(() => [
  ...(canAcknowledge.value ? [{ label: _t('Acknowledge'), value: 'acknowledge' }] : []),
  ...(canDowntime.value ? [{ label: _t('Schedule downtime'), value: 'downtime' }] : [])
])

const recursive = ref(true)
const comment = ref('')
const sticky = ref(true)
const notify = ref(true)
const persistent = ref(false)
const { range, isValid, asIso } = useDowntimeWindow()

const hosts = computed(() => folderHosts(props.folder, recursive.value))
// Checkmk refuses to acknowledge a host that has no problem, and a tile that is
// red for a failing service belongs to a host that may well be UP.
const targets = computed<CommandTarget[]>(() =>
  hosts.value
    .filter(({ state }) => mode.value === 'downtime' || isProblemState(state))
    .map(({ host, site }) => ({ host, service: null, site }))
)
const skipped = computed(() => hosts.value.length - targets.value.length)

const { submitting, progress, succeeded, pending, error, blocked, submit, reject } =
  useBulkCommandSubmit({
    what: 'folder-bulk-command',
    targets: () => targets.value,
    onDone: () => emit('close'),
    send: (target) => {
      if (mode.value === 'acknowledge') {
        return commands.acknowledgeHost(target.host, {
          comment: comment.value,
          sticky: sticky.value,
          notify: notify.value,
          persistent: persistent.value
        })
      }
      const window = asIso()
      return commands.downtimeHost(target.host, {
        startTime: window.start,
        endTime: window.end,
        comment: comment.value
      })
    }
  })

function onSubmit(): void {
  if (!comment.value.trim() || pending.value === 0) {
    return
  }
  if (mode.value === 'downtime' && !isValid.value) {
    reject(_t('Please provide a start and an end time, with the end after the start.'))
    return
  }
  void submit()
}
</script>

<template>
  <MapsModal
    :open="true"
    :title="_t('Folder actions — %{folder}', { folder: folder.title })"
    closable
    @close="emit('close')"
  >
    <CmkToggleButtonGroup v-if="modes.length > 1" v-model="mode" :options="modes" spacing="none" />

    <p class="maps-folder-bulk-action-modal__subtitle">
      {{
        _tn(
          'Applies to %{count} host in “%{folder}”.',
          'Applies to %{count} hosts in “%{folder}”.',
          targets.length,
          { count: targets.length, folder: folder.title }
        )
      }}
    </p>
    <p v-if="skipped" class="maps-folder-bulk-action-modal__skipped">
      {{
        _tn(
          '%{count} host without a problem left out.',
          '%{count} hosts without a problem left out.',
          skipped,
          { count: skipped }
        )
      }}
    </p>
    <CmkCheckbox v-model="recursive" :label="_t('Include sub-folders')" />

    <div class="maps-folder-bulk-action-modal__fields">
      <div class="maps-folder-bulk-action-modal__field">
        <CmkLabel>{{ _t('Comment') }}</CmkLabel>
        <CmkInput v-model="comment" field-size="fill" :placeholder="`${_t('Comment')}…`" />
      </div>
      <template v-if="mode === 'acknowledge'">
        <CmkCheckbox v-model="sticky" :label="_t('Sticky (stays until OK)')" />
        <CmkCheckbox v-model="notify" :label="_t('Send notification')" />
        <CmkCheckbox v-model="persistent" :label="_t('Persistent')" />
      </template>
      <div v-else class="maps-folder-bulk-action-modal__field">
        <CmkLabel>{{ _t('Downtime period') }}</CmkLabel>
        <CmkTimeRangePicker v-model="range" :label="_t('Downtime period')" />
      </div>
    </div>

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
        variant="primary"
        :disabled="blocked || !comment.trim() || pending === 0"
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

.maps-folder-bulk-action-modal__skipped {
  margin: 0 0 var(--dimension-3);
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-folder-bulk-action-modal__fields {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-top: var(--dimension-5);
}

.maps-folder-bulk-action-modal__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}
</style>
