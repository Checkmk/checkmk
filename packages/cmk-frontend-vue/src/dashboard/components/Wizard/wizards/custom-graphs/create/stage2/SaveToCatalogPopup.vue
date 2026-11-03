<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkPopup from 'cmk-ui-library/components/CmkPopup.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'
import { DialogTitle } from 'reka-ui'
import { computed, nextTick, onMounted, ref } from 'vue'

import {
  type CreateCustomGraphRequest,
  createCustomGraph,
  listCustomGraphMetadata
} from '@/graphing/designer/api'

import type { EmbeddedGraphDefinition } from '../../editor/types'

const { _t } = usei18n()

// Mounted for one opening only, so every opening starts with an empty form.
const props = defineProps<{
  definition: EmbeddedGraphDefinition
  /** Starting point of the suggested ID, e.g. `<source>_clone` */
  nameBase?: string | undefined
  /** Whether the widget the graph is saved from already sits on the dashboard. */
  edit: boolean
}>()

const emit = defineEmits<{
  saved: [name: string]
  close: []
}>()

// The defaults of the legacy "new custom graph" page.
const METADATA: CreateCustomGraphRequest['metadata'] = {
  description: '',
  topic: 'my_workplace',
  sort_index: 99,
  hidden: false,
  is_show_more: false,
  public: { type: 'private' }
}
const NAME_PATTERN = /^[a-zA-Z_][-a-zA-Z0-9_]*$/

// Like the legacy page: `base` if unused, else the first free `<base>_<n>`, where a trailing `_<n>`
// of `base` itself is replaced rather than extended.
function suggestName(usedNames: Set<string>, base: string | undefined): string {
  if (base !== undefined && !usedNames.has(base)) {
    return base
  }
  const template = base === undefined ? 'custom_graph' : base.replace(/_\d+$/, '')
  let number = 1
  while (usedNames.has(`${template}_${number}`)) {
    number++
  }
  return `${template}_${number}`
}

const titleId = useId()
const nameId = useId()
const titleInput = ref<{ focus: () => void } | null>(null)

const title = ref('')
const name = ref('')
const rejectedName = ref<string | null>(null)
const saveError = ref<TranslatedString | null>(null)
const isSaving = ref(false)
const hasAttemptedSave = ref(false)

const titleErrors = computed(() =>
  hasAttemptedSave.value && title.value.trim() === '' ? [_t('Enter a title.')] : []
)
// A malformed ID is flagged while typing, an empty one only on save.
const nameErrors = computed(() => {
  if (name.value === '') {
    return hasAttemptedSave.value ? [_t('Enter an ID.')] : []
  }
  if (!NAME_PATTERN.test(name.value)) {
    return [
      _t(
        'Start with a letter or an underscore, then use only letters, digits, hyphens (-) and underscores (_).'
      )
    ]
  }
  return name.value === rejectedName.value
    ? [_t('You already have a custom graph with this ID.')]
    : []
})
async function suggestId(): Promise<void> {
  try {
    const collection = await listCustomGraphMetadata()
    const usedNames = new Set(collection.value.flatMap((entry) => entry.id ?? []))
    const suggestion = suggestName(usedNames, props.nameBase)
    // Only suggest if nothing was typed yet
    if (name.value === '') {
      name.value = suggestion
    }
  } catch (e) {
    // Without a suggestion the user enters the ID; anything but a failed request is a bug.
    if (!(e instanceof CmkApiError)) {
      throw e
    }
  }
}
void suggestId()

// CmkPopup moves the focus only when `open` changes, which it never does here.
onMounted(async () => {
  await nextTick()
  titleInput.value?.focus()
})

async function save() {
  if (isSaving.value) {
    return
  }
  hasAttemptedSave.value = true
  if (titleErrors.value.length > 0 || nameErrors.value.length > 0) {
    return
  }
  isSaving.value = true
  saveError.value = null
  const savedName = name.value
  try {
    await createCustomGraph({
      name: savedName,
      title: title.value.trim(),
      metadata: METADATA,
      content: props.definition
    })
    emit('saved', savedName)
  } catch (e) {
    if (e instanceof CmkApiError && e.statusCode === 409) {
      rejectedName.value = savedName
    } else {
      saveError.value =
        e instanceof Error ? untranslated(e.message) : _t('The graph could not be saved.')
    }
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <CmkPopup :open="true" @close="emit('close')">
    <form class="db-save-to-catalog-popup" @submit.prevent="save">
      <div class="db-save-to-catalog-popup__header">
        <DialogTitle>
          <CmkHeading type="h2">{{ _t('Save to custom graph catalog') }}</CmkHeading>
        </DialogTitle>
        <CmkIconButton name="close" size="small" :title="_t('Close')" @click="emit('close')" />
      </div>
      <CmkParagraph>
        {{ _t('Save this graph to the catalog to make it reusable across dashboards.') }}<br />
        {{ _t('Provide a title and unique ID.') }}
      </CmkParagraph>
      <div class="db-save-to-catalog-popup__field">
        <CmkLabel :for="titleId"
          >{{ _t('Title') }}
          <span class="db-save-to-catalog-popup__required">{{ _t('(required)') }}</span></CmkLabel
        >
        <CmkInput
          :id="titleId"
          ref="titleInput"
          v-model="title"
          field-size="medium"
          :external-errors="titleErrors"
        />
      </div>
      <div class="db-save-to-catalog-popup__field">
        <CmkLabel :for="nameId"
          >{{ _t('Unique ID') }}
          <span class="db-save-to-catalog-popup__required">{{ _t('(required)') }}</span></CmkLabel
        >
        <CmkInput :id="nameId" v-model="name" field-size="medium" :external-errors="nameErrors" />
      </div>
      <CmkAlert v-if="saveError !== null" variant="error" :text="saveError" />
      <div class="db-save-to-catalog-popup__buttons">
        <CmkButton variant="info" :disabled="isSaving" @click="save">{{
          edit ? _t('Save to catalog & save widget') : _t('Save to catalog & place widget')
        }}</CmkButton>
        <CmkButton variant="optional" :icon="{ name: 'cancel' }" @click="emit('close')">{{
          _t('Cancel')
        }}</CmkButton>
      </div>
    </form>
  </CmkPopup>
</template>

<style scoped>
.db-save-to-catalog-popup {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  width: 100%;
}

.db-save-to-catalog-popup__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
}

.db-save-to-catalog-popup__required {
  color: var(--color-corporate-green-50);
  font-weight: var(--font-weight-default);
}

.db-save-to-catalog-popup__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.db-save-to-catalog-popup__buttons {
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-4);
}
</style>
