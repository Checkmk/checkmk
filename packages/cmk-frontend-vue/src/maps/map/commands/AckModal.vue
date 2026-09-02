<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Acknowledge a problem: say that somebody has seen it and is on it, so it stops
notifying and stops reading as unhandled.

A group is acknowledged in one call rather than member by member -- that is
Checkmk's own bulk command, and it either applies to all of them or to none.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref } from 'vue'

import type { AcknowledgeOptions } from '@/maps/api/commands'
import { useMapsApis } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { MapElement } from '@/maps/types/api'
import { objectDisplayName } from '@/maps/utils/dropdownOptions'

import CommandFeedback from './CommandFeedback.vue'
import { describeGroupCommandError, messageOf } from './commandErrors'
import { useCommandSubmit } from './useCommandSubmit'

const { commands } = useMapsApis()

const props = defineProps<{
  object: MapElement
  checkmkUrl: string
}>()

const emit = defineEmits<{ close: [] }>()

const { _t } = usei18n()

const comment = ref('')
const sticky = ref(true)
const notify = ref(true)
const persistent = ref(false)
const commentEl = ref<HTMLInputElement | null>(null)

function options(): AcknowledgeOptions {
  return {
    comment: comment.value,
    sticky: sticky.value,
    notify: notify.value,
    persistent: persistent.value
  }
}

const displayName = computed(() => objectDisplayName(props.object, _t))

const isGroup = computed(
  () => props.object.type === 'hostgroup' || props.object.type === 'servicegroup'
)
const groupTypeLabel = computed(() =>
  props.object.type === 'hostgroup' ? _t('host group') : _t('service group')
)

onMounted(() => commentEl.value?.focus())

const { submitting, succeeded, error, blocked, submit } = useCommandSubmit({
  fallbackError: _t('Failed to acknowledge'),
  describeError: (caught) =>
    describeGroupCommandError(
      messageOf(caught, _t('Failed to acknowledge')),
      isGroup.value,
      groupTypeLabel.value,
      _t
    ),
  onDone: () => emit('close'),
  send: async () => {
    if (props.object.type === 'hostgroup' && props.object.group_name) {
      await commands.acknowledgeHostgroup(props.checkmkUrl, props.object.group_name, options())
      return
    }
    if (props.object.type === 'servicegroup' && props.object.group_name) {
      await commands.acknowledgeServicegroup(props.checkmkUrl, props.object.group_name, options())
      return
    }
    if (
      props.object.type === 'service' &&
      props.object.host_name &&
      props.object.service_description
    ) {
      await commands.acknowledgeService(
        props.object.host_name,
        props.object.service_description,
        options()
      )
      return
    }
    if (props.object.host_name) {
      await commands.acknowledgeHost(props.object.host_name, options())
    }
  }
})

// Checkmk requires a comment on an acknowledgement -- it is the record of who
// took it on and why.
function onSubmit(): void {
  if (comment.value.trim()) {
    void submit()
  }
}
</script>

<template>
  <MapsModal :open="true" :title="_t('Acknowledge problem')" closable @close="emit('close')">
    <p class="maps-ack-modal__subtitle">{{ displayName }}</p>
    <p
      v-if="isGroup"
      class="maps-ack-modal__group-hint"
      :title="
        _t(
          'Checkmk fans this command out across all members; partial failures abort the operation.'
        )
      "
    >
      {{ _t('Applies to every member of the %{type}', { type: groupTypeLabel }) }}
    </p>

    <div class="maps-ack-modal__fields">
      <div>
        <label class="maps-ack-modal__label">{{ _t('Comment') }}</label>
        <CmkInput
          ref="commentEl"
          v-model="comment"
          field-size="fill"
          :placeholder="`${_t('Comment')}…`"
        />
      </div>
      <CmkCheckbox v-model="sticky" :label="_t('Sticky (stays until OK)')" />
      <CmkCheckbox v-model="notify" :label="_t('Send notification')" />
      <CmkCheckbox v-model="persistent" :label="_t('Persistent')" />
    </div>

    <CommandFeedback
      :error="error"
      :succeeded="succeeded"
      :succeeded-text="_t('Acknowledgement set')"
    />

    <template #footer>
      <CmkButton variant="secondary" @click="emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton variant="primary" :disabled="blocked || !comment.trim()" @click="onSubmit">
        {{ submitting ? _t('Acknowledging…') : _t('Acknowledge') }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-ack-modal__subtitle {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  margin: calc(-1 * var(--dimension-4)) 0 0;
}

/* A bulk command deserves a word of warning before it is sent. */
.maps-ack-modal__group-hint {
  font-size: var(--font-size-normal);
  color: var(--color-yellow-50);
  margin: calc(-1 * var(--dimension-4)) 0 0;
}

.maps-ack-modal__fields {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-top: var(--dimension-5);
}

.maps-ack-modal__label {
  display: block;
  font-size: var(--font-size-normal);
  font-weight: 500;
  color: var(--font-color-dimmed);
  margin-bottom: var(--dimension-3);
}
</style>
