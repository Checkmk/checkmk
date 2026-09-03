<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import MapsModal from '@/maps/shared/components/MapsModal.vue'

type BundleKind = 'static' | 'location'

defineProps<{ hostCount: number }>()
const emit = defineEmits<{ close: []; confirm: [payload: { name: string; kind: BundleKind }] }>()

const { _t } = usei18n()

const name = ref('')
const kind = ref<BundleKind>('location')

const typeCards = computed<{ kind: BundleKind; title: string; desc: string }[]>(() => [
  {
    kind: 'location',
    title: _t('Location-bound'),
    desc: _t('Hosts at this coordinate — new hosts added there join automatically.')
  },
  {
    kind: 'static',
    title: _t('Fixed selection'),
    desc: _t('Exactly the selected hosts — does not change on its own.')
  }
])

function submit() {
  emit('confirm', { name: name.value.trim(), kind: kind.value })
}
</script>

<template>
  <MapsModal :open="true" :title="_t('Bundle into a location')" closable @close="$emit('close')">
    <form class="maps-bundle-dialog__form" @submit.prevent="submit">
      <p class="maps-bundle-dialog__intro">
        {{ _t('%{n} hosts will be merged into one worst-state location icon.', { n: hostCount }) }}
      </p>
      <div class="maps-bundle-dialog__field">
        <label class="maps-bundle-dialog__label">{{ _t('Name (optional)') }}</label>
        <CmkInput
          v-model="name"
          :placeholder="_t('e.g. Datacenter Zürich')"
          field-size="fill"
          @keydown.enter.prevent="submit"
        />
      </div>
      <div class="maps-bundle-dialog__field">
        <div
          class="maps-bundle-dialog__type-grid"
          role="radiogroup"
          :aria-label="_t('Bundle type')"
        >
          <button
            v-for="opt in typeCards"
            :key="opt.kind"
            type="button"
            role="radio"
            :aria-checked="kind === opt.kind"
            class="maps-bundle-dialog__type-card"
            :class="{ 'maps-bundle-dialog__type-card--selected': kind === opt.kind }"
            @click="kind = opt.kind"
          >
            <span class="maps-bundle-dialog__type-card-title">{{ opt.title }}</span>
            <span class="maps-bundle-dialog__type-card-desc">{{ opt.desc }}</span>
          </button>
        </div>
      </div>
    </form>

    <template #footer>
      <CmkButton variant="secondary" @click="$emit('close')">{{ _t('Cancel') }}</CmkButton>
      <CmkButton variant="primary" @click="submit">{{ _t('Bundle') }}</CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-bundle-dialog__form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  min-width: 380px;
}

.maps-bundle-dialog__intro {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-bundle-dialog__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.maps-bundle-dialog__label {
  font-size: var(--font-size-normal);
  font-weight: 500;
  color: var(--font-color-dimmed);
}

.maps-bundle-dialog__type-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--dimension-3);
}

.maps-bundle-dialog__type-card {
  text-align: left;
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  transition:
    border-color 120ms,
    background-color 120ms;
}

.maps-bundle-dialog__type-card:hover {
  border-color: var(--color-corporate-green-50);
}

.maps-bundle-dialog__type-card--selected {
  border-color: var(--color-corporate-green-50);
  background: color-mix(
    in srgb,
    var(--color-corporate-green-50) 10%,
    var(--default-form-element-bg-color)
  );
}

.maps-bundle-dialog__type-card-title {
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

.maps-bundle-dialog__type-card-desc {
  font-size: 11px;
  color: var(--font-color-dimmed);
  line-height: 1.35;
}
</style>
