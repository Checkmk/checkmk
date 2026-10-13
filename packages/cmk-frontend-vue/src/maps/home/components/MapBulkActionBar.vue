<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

const props = defineProps<{
  count: number
  busy?: boolean
  selectAllChecked: boolean
  selectAllLabel: string
}>()
const emit = defineEmits<{
  cancel: []
  delete: []
  edit: []
  'toggle-select-all': [checked: boolean]
}>()

const { _t, _tn } = usei18n()
const ariaLabel = computed(() =>
  _tn('%{n} selected', '%{n} selected', props.count, { n: props.count })
)
</script>

<template>
  <Transition name="maps-map-bulk-action-bar__bar">
    <div v-if="count > 0" class="maps-map-bulk-action-bar" role="region" :aria-label="ariaLabel">
      <div class="maps-map-bulk-action-bar__info">
        <CmkIconButton
          name="close"
          size="small"
          :title="_t('Cancel')"
          :aria-label="_t('Cancel')"
          @click="emit('cancel')"
        />
        <span class="maps-map-bulk-action-bar__count">{{
          _tn('%{n} selected', '%{n} selected', count, { n: count })
        }}</span>
        <label class="maps-map-bulk-action-bar__selectall">
          <CmkCheckbox
            :model-value="selectAllChecked"
            @update:model-value="emit('toggle-select-all', $event)"
          />
          <span>{{ selectAllLabel }}</span>
        </label>
      </div>
      <div class="maps-map-bulk-action-bar__actions">
        <CmkButton variant="primary" :disabled="busy" @click="emit('edit')">
          {{ _t('Edit') }}
        </CmkButton>
        <CmkButton variant="danger" :disabled="busy" @click="emit('delete')">
          {{ _t('Delete') }}
        </CmkButton>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.maps-map-bulk-action-bar {
  position: fixed;
  bottom: var(--dimension-6);
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--dimension-4) var(--dimension-6);
  padding: var(--dimension-3) var(--dimension-5);
  background: var(--ux-theme-3);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  box-shadow: 0 8px 24px rgb(0 0 0 / 25%);
  max-width: calc(100vw - 24px);
}

.maps-map-bulk-action-bar__info {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  flex-shrink: 0;
}

.maps-map-bulk-action-bar__actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  flex-shrink: 0;
}

.maps-map-bulk-action-bar__count {
  font-weight: var(--font-weight-bold);
  white-space: nowrap;
}

.maps-map-bulk-action-bar__selectall {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
  color: var(--font-color-dimmed);
  font-size: 0.9em;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

/* The bar is one row that must not wrap, so the shared buttons in it keep
   their labels on one line. ``:deep`` is how this package reaches a child
   component's root; stylelint does not know the selector. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.maps-map-bulk-action-bar__actions :deep(button) {
  white-space: nowrap;
  flex-shrink: 0;
}

.maps-map-bulk-action-bar__bar-enter-active,
.maps-map-bulk-action-bar__bar-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.maps-map-bulk-action-bar__bar-enter-from,
.maps-map-bulk-action-bar__bar-leave-to {
  opacity: 0;
  transform: translate(-50%, 12px);
}
</style>
