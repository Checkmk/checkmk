<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Leave a note on a host or service, so the next person to open it knows what is
already being done about it.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref } from 'vue'

import { useMapsApis } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { MapElement } from '@/maps/types/api'
import { objectDisplayName } from '@/maps/utils/dropdownOptions'

import CommandFeedback from './CommandFeedback.vue'
import { useCommandSubmit } from './useCommandSubmit'

const { commands } = useMapsApis()

const { _t } = usei18n()

const props = defineProps<{
  object: MapElement
  checkmkUrl: string
}>()

const emit = defineEmits<{ close: [] }>()

const comment = ref('')
const commentEl = ref<HTMLInputElement | null>(null)

onMounted(() => {
  commentEl.value?.focus()
})

const displayName = computed(() => objectDisplayName(props.object, _t))

const { submitting, succeeded, error, blocked, submit } = useCommandSubmit({
  fallbackError: _t('Failed to add comment'),
  onDone: () => emit('close'),
  send: async () => {
    if (
      props.object.type === 'service' &&
      props.object.host_name &&
      props.object.service_description
    ) {
      await commands.addCommentService(
        props.object.host_name,
        props.object.service_description,
        comment.value
      )
      return
    }
    if (props.object.host_name) {
      await commands.addCommentHost(props.object.host_name, comment.value)
    }
  }
})

// A comment with no text says nothing; the command is refused rather than sent.
function onSubmit(): void {
  if (comment.value.trim()) {
    void submit()
  }
}
</script>

<template>
  <MapsModal :open="true" :title="_t('Add comment')" closable @close="emit('close')">
    <p class="maps-comment-modal__subtitle">{{ displayName }}</p>

    <div class="maps-comment-modal__field">
      <label class="maps-comment-modal__label">{{ _t('Comment') }}</label>
      <CmkInput
        ref="commentEl"
        v-model="comment"
        field-size="fill"
        :placeholder="`${_t('Comment')}…`"
        @keydown.enter="onSubmit"
      />
    </div>

    <CommandFeedback :error="error" :succeeded="succeeded" :succeeded-text="_t('Comment added')" />

    <template #footer>
      <CmkButton variant="secondary" @click="emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton variant="primary" :disabled="blocked || !comment.trim()" @click="onSubmit">
        {{ submitting ? _t('Adding…') : _t('Add comment') }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-comment-modal__subtitle {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  margin: calc(-1 * var(--dimension-4)) 0 0;
}

.maps-comment-modal__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  margin-top: var(--dimension-5);
}

.maps-comment-modal__label {
  font-size: var(--font-size-normal);
  font-weight: 500;
  color: var(--font-color-dimmed);
}
</style>
