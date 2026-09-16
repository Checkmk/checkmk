<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalSettingsHint } from 'cmk-shared-typing/typescript/global_settings'
import type { CmkAlertBoxProps } from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkCopy from 'cmk-ui-library/components/CmkCopy.vue'
import CmkHtml from 'cmk-ui-library/components/CmkHtml.vue'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, toRaw, watch } from 'vue'

import FormEdit from '@/form/FormEdit.vue'
import FormReadonly from '@/form/FormReadonly.vue'
import FormHelp from '@/form/private/FormHelp.vue'

import { isExplicitIn } from '../lib/origin'
import type { EditorSession } from '../useGlobalSettingsEditor'
import GlobalSettingsRow from './GlobalSettingsRow.vue'

const { _t } = usei18n()

const props = defineProps<{
  session: EditorSession
}>()

const emit = defineEmits<{
  close: []
}>()

const variable = computed(() => props.session.variable)
const inSiteScope = computed(() => props.session.scope.type === 'site')
const removable = computed(() => isExplicitIn(variable.value, props.session.scope))
const error = computed(() => props.session.error)
const specWithoutTopLevelHelp = computed(() => ({ ...variable.value.spec, help: '' }))

const draft = ref<unknown>(structuredClone(toRaw(props.session.variable.value)))
const confirmResetOpen = ref(false)

watch(
  () => props.session.variable.value,
  (value) => {
    draft.value = structuredClone(toRaw(value))
  }
)

function confirmReset(): void {
  confirmResetOpen.value = false
  void props.session.reset()
}

function valuesEqual(a: unknown, b: unknown): boolean {
  if (a === b) {
    return true
  }
  if (Array.isArray(a) || Array.isArray(b)) {
    return (
      Array.isArray(a) &&
      Array.isArray(b) &&
      a.length === b.length &&
      a.every((entry, index) => valuesEqual(entry, b[index]))
    )
  }
  if (typeof a === 'object' && typeof b === 'object' && a !== null && b !== null) {
    const entries = Object.entries(a)
    return (
      entries.length === Object.keys(b).length &&
      entries.every(
        ([key, value]) => key in b && valuesEqual(value, (b as Record<string, unknown>)[key])
      )
    )
  }
  return false
}

const isExplicitDefault = computed(
  () =>
    !inSiteScope.value &&
    removable.value &&
    valuesEqual(variable.value.value, variable.value.default_value)
)

const resetButtonLabel = computed<TranslatedString>(() => {
  if (inSiteScope.value) {
    return _t('Remove site-specific value')
  }
  return isExplicitDefault.value ? _t('Remove explicit setting') : _t('Remove modification')
})

const resetConfirmation = computed<{
  heading: TranslatedString
  body: TranslatedString
  confirm: TranslatedString
}>(() => {
  if (inSiteScope.value) {
    return {
      heading: _t('Remove site-specific value?'),
      body: _t('The site will inherit the value from Global settings.'),
      confirm: _t('Remove')
    }
  }
  return isExplicitDefault.value
    ? {
        heading: _t('Remove explicit setting?'),
        body: _t(
          'Removing the explicit value will restore the default value for this site. The value will be inherited from Global settings or the factory settings.'
        ),
        confirm: _t('Remove')
      }
    : {
        heading: _t('Remove modification?'),
        body: _t(
          'The configured value will be discarded and the factory default will be used instead.'
        ),
        confirm: _t('Remove')
      }
})

function hintAlertProps(hint: GlobalSettingsHint): CmkAlertBoxProps {
  return hint.variant === 'info' ? { variant: 'info' } : { variant: 'warning' }
}

const currentStateText = computed<TranslatedString>(() => {
  switch (variable.value.origin) {
    case 'site':
      return _t('This variable is overridden on this site.')
    case 'global':
      return inSiteScope.value
        ? _t('This variable inherits the value from Global settings.')
        : _t('This variable has been modified.')
    default:
      return _t('This variable is at factory settings.')
  }
})
</script>

<template>
  <div class="global-settings-editor">
    <div class="global-settings-editor__actions">
      <CmkButton variant="primary" :disabled="!session.editable" @click="session.save(draft)">
        {{ _t('Save') }}
      </CmkButton>
      <CmkButton
        v-if="removable"
        variant="secondary"
        :icon="{ name: 'reset' }"
        :disabled="!session.editable"
        :title="
          inSiteScope
            ? _t('Remove the value configured for this site')
            : _t('Reset to factory default')
        "
        @click="confirmResetOpen = true"
      >
        {{ resetButtonLabel }}
      </CmkButton>
      <CmkButton variant="optional" :icon="{ name: 'cancel' }" @click="emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
    </div>

    <CmkAlertBox v-if="error !== null" variant="error" :heading="error.heading">
      <span class="global-settings-editor__error">{{ error.message }}</span>
    </CmkAlertBox>

    <CmkAlertBox
      v-if="confirmResetOpen"
      variant="warning"
      :heading="resetConfirmation.heading"
      :main-button="{ title: resetConfirmation.confirm, onclick: confirmReset }"
      :optional-button="{
        title: _t('Cancel'),
        icon: 'cancel',
        onclick: () => (confirmResetOpen = false)
      }"
    >
      {{ resetConfirmation.body }}
    </CmkAlertBox>

    <CmkAlertBox v-if="isExplicitDefault" variant="info" dismissible>
      {{
        _t(
          'This setting uses an explicit value and overrides the factory and Global settings value.'
        )
      }}
    </CmkAlertBox>

    <CmkAlertBox v-for="(hint, index) in variable.hints" :key="index" v-bind="hintAlertProps(hint)">
      <span class="global-settings-editor__hint">
        <CmkHtml :html="hint.text" />
        <template v-if="hint.copyable !== null">
          <code>{{ hint.copyable }}</code>
          <CmkCopy :text="hint.copyable">
            <CmkButton
              size="iconOnly"
              :icon="{ name: 'view-copy' }"
              :aria-label="_t('Copy to clipboard')"
            />
          </CmkCopy>
        </template>
      </span>
    </CmkAlertBox>

    <FormHelp :help="variable.spec.help" />

    <div class="global-settings-editor__sections">
      <CmkCatalogPanel :title="untranslated(variable.spec.title)">
        <GlobalSettingsRow :label="_t('Current setting')" :help="untranslated(variable.spec.help)">
          <FormEdit v-model:data="draft" :spec="specWithoutTopLevelHelp" :backend-validation="[]" />
        </GlobalSettingsRow>
        <GlobalSettingsRow :label="_t('Current state')">
          {{ currentStateText }}
        </GlobalSettingsRow>
      </CmkCatalogPanel>

      <CmkCatalogPanel v-if="inSiteScope" :title="_t('Global settings')">
        <GlobalSettingsRow :label="_t('Global setting')">
          <FormReadonly
            :spec="variable.spec"
            :data="variable.global_value"
            :backend-validation="[]"
          />
        </GlobalSettingsRow>
      </CmkCatalogPanel>

      <CmkCatalogPanel :title="_t('Factory settings')">
        <GlobalSettingsRow :label="_t('Factory setting')">
          <FormReadonly
            :spec="variable.spec"
            :data="variable.default_value"
            :backend-validation="[]"
          />
        </GlobalSettingsRow>
      </CmkCatalogPanel>

      <CmkCatalogPanel v-if="variable.site_overrides.length > 0" :title="_t('Site overrides')">
        <p class="global-settings-editor__overrides-intro">
          {{ _t('This setting is overridden by the following sites:') }}
        </p>
        <ul class="global-settings-editor__overrides">
          <li
            v-for="override in variable.site_overrides"
            :key="override.site_id"
            class="global-settings-editor__override"
          >
            <span class="global-settings-editor__override-title">
              {{ override.title }}
            </span>
            <CmkLink :href="override.url" class="global-settings-editor__override-link">
              {{ _t('Open site settings') }}
            </CmkLink>
          </li>
        </ul>
      </CmkCatalogPanel>
    </div>
  </div>
</template>

<style scoped>
.global-settings-editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 20px;
}

.global-settings-editor__actions {
  display: flex;
  gap: 8px;
}

.global-settings-editor__sections {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.global-settings-editor__error {
  white-space: pre-wrap;
}

.global-settings-editor__hint {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.global-settings-editor__overrides-intro {
  margin: 0 0 12px;
}

.global-settings-editor__overrides {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.global-settings-editor__override {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 2px;
  background: var(--ux-theme-6);
}

.global-settings-editor__override-title {
  font-weight: bold;
}

.global-settings-editor__override-link {
  width: auto;
}
</style>
