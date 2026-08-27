<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalSettingsVariable } from 'cmk-shared-typing/typescript/global_settings'
import CmkAccordion from 'cmk-ui-library/components/CmkAccordion/CmkAccordion.vue'
import CmkAccordionItem from 'cmk-ui-library/components/CmkAccordion/CmkAccordionItem.vue'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkHelpText from 'cmk-ui-library/components/CmkHelpText.vue'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, toRaw } from 'vue'

import FormEdit from '@/form/FormEdit.vue'
import FormReadonly from '@/form/FormReadonly.vue'

const { _t } = usei18n()

const props = defineProps<{
  variable: GlobalSettingsVariable
  title: string
}>()

const emit = defineEmits<{
  close: []
  save: [value: unknown]
  reset: []
}>()

const CURRENT_SECTION = 'current-setting'
const FACTORY_SECTION = 'factory-settings'
const SITE_OVERRIDES_SECTION = 'site-overrides'

const draft = ref<unknown>(structuredClone(toRaw(props.variable.value)))
const confirmReset = ref(false)
const openedSections = ref<string[]>([CURRENT_SECTION, FACTORY_SECTION])

const resetButtonLabel = computed<TranslatedString>(() => _t('Remove modification'))

const resetConfirmation = computed<{
  heading: TranslatedString
  body: TranslatedString
  confirm: TranslatedString
}>(() => ({
  heading: _t('Remove modification?'),
  body: _t('The configured value will be discarded and the factory default will be used instead.'),
  confirm: _t('Remove')
}))

const currentStateText = computed<TranslatedString>(() =>
  props.variable.modified
    ? _t('This variable has been modified.')
    : _t('This variable is at factory settings.')
)
</script>

<template>
  <CmkSlideInDialog
    open
    size="small"
    :header="{ title: title, closeButton: true }"
    @close="emit('close')"
  >
    <div class="global-settings-edit-slide-in">
      <div class="global-settings-edit-slide-in__actions">
        <CmkButton variant="primary" @click="emit('save', draft)">{{ _t('Save') }}</CmkButton>
        <CmkButton
          v-if="variable.modified"
          variant="secondary"
          :icon="{ name: 'reset' }"
          :title="_t('Reset to factory default')"
          @click="confirmReset = true"
        >
          {{ resetButtonLabel }}
        </CmkButton>
        <CmkButton variant="optional" :icon="{ name: 'cancel' }" @click="emit('close')">
          {{ _t('Cancel') }}
        </CmkButton>
      </div>

      <CmkAlertBox
        v-if="confirmReset"
        variant="warning"
        :heading="resetConfirmation.heading"
        :main-button="{ title: resetConfirmation.confirm, onclick: () => emit('reset') }"
        :optional-button="{
          title: _t('Cancel'),
          icon: 'cancel',
          onclick: () => (confirmReset = false)
        }"
      >
        {{ resetConfirmation.body }}
      </CmkAlertBox>

      <CmkAccordion v-model="openedSections" :min-open="0" :max-open="0">
        <CmkAccordionItem :value="CURRENT_SECTION">
          <template #header>
            <span class="global-settings-edit-slide-in__section-title">{{
              variable.spec.title
            }}</span>
          </template>
          <template v-if="variable.spec.help" #header-right>
            <CmkHelpText :help="variable.spec.help as TranslatedString" />
          </template>
          <template #content>
            <div class="global-settings-edit-slide-in__row">
              <span class="global-settings-edit-slide-in__label">
                <span>{{ _t('Current setting') }}</span>
                <span class="global-settings-edit-slide-in__leader"></span>
              </span>
              <FormEdit v-model:data="draft" :spec="variable.spec" :backend-validation="[]" />
            </div>
          </template>
        </CmkAccordionItem>

        <CmkAccordionItem :value="FACTORY_SECTION">
          <template #header>
            <span class="global-settings-edit-slide-in__section-title">
              {{ _t('Factory settings') }}
            </span>
          </template>
          <template #content>
            <div class="global-settings-edit-slide-in__row">
              <span class="global-settings-edit-slide-in__label">
                <span>{{ _t('Factory setting') }}</span>
                <span class="global-settings-edit-slide-in__leader"></span>
              </span>
              <FormReadonly
                :spec="variable.spec"
                :data="variable.default_value"
                :backend-validation="[]"
              />
            </div>
            <div class="global-settings-edit-slide-in__row">
              <span class="global-settings-edit-slide-in__label">
                <span>{{ _t('Current state') }}</span>
                <span class="global-settings-edit-slide-in__leader"></span>
              </span>
              <span>{{ currentStateText }}</span>
            </div>
          </template>
        </CmkAccordionItem>

        <CmkAccordionItem v-if="variable.site_overrides.length > 0" :value="SITE_OVERRIDES_SECTION">
          <template #header>
            <span class="global-settings-edit-slide-in__section-title">
              {{ _t('Site overrides') }}
            </span>
          </template>
          <template #content>
            <p class="global-settings-edit-slide-in__overrides-intro">
              {{ _t('This setting is overridden by the following sites:') }}
            </p>
            <ul class="global-settings-edit-slide-in__overrides">
              <li
                v-for="override in variable.site_overrides"
                :key="override.site_id"
                class="global-settings-edit-slide-in__override"
              >
                <span class="global-settings-edit-slide-in__override-title">
                  {{ override.title }}
                </span>
                <CmkLink :href="override.url" class="global-settings-edit-slide-in__override-link">
                  {{ _t('Open site settings') }}
                </CmkLink>
              </li>
            </ul>
          </template>
        </CmkAccordionItem>
      </CmkAccordion>
    </div>
  </CmkSlideInDialog>
</template>

<style scoped>
.global-settings-edit-slide-in {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 20px;
}

.global-settings-edit-slide-in__actions {
  display: flex;
  gap: 8px;
}

.global-settings-edit-slide-in__section-title {
  font-weight: bold;
}

.global-settings-edit-slide-in__row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
}

.global-settings-edit-slide-in__label {
  display: flex;
  flex: 0 0 140px;
  align-items: center;
  gap: 4px;
  height: 16px;
  overflow: hidden;
  color: var(--font-color-dimmed);
}

.global-settings-edit-slide-in__leader {
  flex: 1 1 auto;
  min-width: 1px;
  height: 1em;
  border-bottom: 1px dotted var(--font-color-dimmed);
}

.global-settings-edit-slide-in__overrides-intro {
  margin: 0 0 12px;
}

.global-settings-edit-slide-in__overrides {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.global-settings-edit-slide-in__override {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 2px;
  background: var(--ux-theme-6);
}

.global-settings-edit-slide-in__override-title {
  font-weight: bold;
}

.global-settings-edit-slide-in__override-link {
  width: auto;
}
</style>
