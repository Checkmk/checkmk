<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  ValidationMessage,
  VueFormspecComponents
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref, watch } from 'vue'

import FormEdit from '@/form/FormEdit.vue'

import { useMapsApis } from '@/maps/services/context'
import { asFormSpecSchema } from '@/maps/utils/formSpec'

const props = defineProps<{
  open: boolean
  names: string[]
  aliases: string[]
  saving?: boolean
}>()

const emit = defineEmits<{
  cancel: []
  apply: [updates: Record<string, unknown>]
}>()

const { _t } = usei18n()
const { formSchemas } = useMapsApis()

type Schema = NonNullable<VueFormspecComponents['components']>

const formSchema = ref<Schema | null>(null)
const schemaLoading = ref(true)
const formSpecData = ref<Record<string, unknown>>({})
const formBackendValidation = ref<ValidationMessage[]>([])

const previewAliases = computed(() => {
  if (props.aliases.length === 0) {
    return ''
  }
  const head = props.aliases.slice(0, 4).join(', ')
  const rest = props.aliases.length - 4
  return rest > 0 ? _t('%{head}, … and %{n} more', { head, n: rest }) : head
})

const hasActiveFields = computed(() => Object.keys(formSpecData.value).length > 0)

async function loadSchema() {
  schemaLoading.value = true
  try {
    // Only the schema: the bag stays empty, because an empty bulk form means
    // "overwrite nothing" and prefilled values would overwrite every map.
    const { schema } = await formSchemas.fetch('map_bulk_metadata')
    formSchema.value = asFormSpecSchema(schema)
  } catch {
    formSchema.value = null
  } finally {
    schemaLoading.value = false
  }
}

/**
 * The ticked fields as they are stored.
 *
 * A form's values are not the stored ones — a single-choice field carries an
 * opaque id per element — so the bag goes back through the form spec on the
 * server before it is applied to any map.
 */
async function apply() {
  const result = await formSchemas.parse('map_bulk_metadata', { ...formSpecData.value })
  if (result.validation) {
    formBackendValidation.value = result.validation
    return
  }
  emit('apply', result.data)
}

onMounted(loadSchema)

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      formSpecData.value = {}
      formBackendValidation.value = []
    }
  }
)

defineExpose({
  setBackendValidation: (msgs: ValidationMessage[]) => {
    formBackendValidation.value = msgs
  }
})
</script>

<template>
  <CmkSlideInDialog
    :open="open"
    :header="{ title: _t('Edit %{n} maps', { n: names.length }), closeButton: true }"
    size="small"
    @close="emit('cancel')"
  >
    <div class="maps-map-bulk-edit-slide-in__shell">
      <p class="maps-map-bulk-edit-slide-in__intro">
        {{
          _t(
            'Tick the fields you want to overwrite on every selected map. Unchecked fields stay untouched.'
          )
        }}
      </p>
      <p v-if="previewAliases" class="maps-map-bulk-edit-slide-in__preview">
        {{ previewAliases }}
      </p>
      <div class="maps-map-bulk-edit-slide-in__body">
        <FormEdit
          v-if="formSchema"
          v-model:data="formSpecData"
          :spec="formSchema"
          :backend-validation="formBackendValidation"
        />
        <CmkLoading v-else-if="schemaLoading" />
        <p v-else class="maps-map-bulk-edit-slide-in__error">
          {{ _t('Could not load the bulk-edit form.') }}
        </p>
      </div>
      <div class="maps-map-bulk-edit-slide-in__footer">
        <CmkButton variant="secondary" :disabled="saving" @click="emit('cancel')">
          {{ _t('Cancel') }}
        </CmkButton>
        <CmkButton variant="primary" :disabled="saving || !hasActiveFields" @click="void apply()">
          {{ _t('Apply to %{n} maps', { n: names.length }) }}
        </CmkButton>
      </div>
    </div>
  </CmkSlideInDialog>
</template>

<style scoped>
.maps-map-bulk-edit-slide-in__shell {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  padding: var(--dimension-5);
  min-width: 480px;
  max-width: 640px;
}

.maps-map-bulk-edit-slide-in__intro {
  color: var(--font-color);
  font-size: var(--font-size-large);
}

.maps-map-bulk-edit-slide-in__preview {
  color: var(--font-color-dimmed);
  font-size: 0.9em;
  font-style: italic;
}

.maps-map-bulk-edit-slide-in__body {
  flex: 1;
  min-height: 200px;
}

.maps-map-bulk-edit-slide-in__error {
  color: var(--color-light-red-40);
}

.maps-map-bulk-edit-slide-in__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-3);
  padding-top: var(--dimension-4);
  border-top: 1px solid var(--default-border-color);
  margin-top: var(--dimension-4);
}
</style>
