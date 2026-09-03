<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A folder-tree map draws Checkmk's own folder hierarchy: which part of it, how
much of it is unfolded, and what is left out.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkSwitch from 'cmk-ui-library/components/CmkSwitch.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref } from 'vue'

import EditField from '@/maps/map/edit/components/EditField.vue'
import FolderTreeSitesSelect from '@/maps/map/edit/settings/components/FolderTreeSitesSelect.vue'
import SettingsSection from '@/maps/map/edit/settings/components/SettingsSection.vue'
import type { SettingsForm } from '@/maps/map/edit/settings/settingsForm'
import { useMapsApis } from '@/maps/services/context'

const form = defineModel<SettingsForm>('form', { required: true })

const { _t } = usei18n()
const { objects } = useMapsApis()

const folders = ref<{ path: string; title: string }[]>([])
const sites = ref<{ id: string; alias: string }[]>([])

onMounted(async () => {
  if (!form.value.connection_id) {
    return
  }
  const [foundFolders, foundSites] = await Promise.all([
    objects.fetchFolders().catch(() => []),
    objects.fetchSites().catch(() => [])
  ])
  folders.value = foundFolders
  sites.value = foundSites
})

const rootFolderOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '', title: _t('(all folders)') },
    ...folders.value.map((folder) => ({ name: folder.path, title: untranslated(folder.title) }))
  ]
}))

const defaultViewOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'list', title: _t('List (tree)') },
    { name: 'map', title: _t('Map (treemap)') }
  ]
}))

const severityOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'any', title: _t('Any problem (incl. WARNING)') },
    { name: 'critical', title: _t('Only critical & down') }
  ]
}))

// The wire shape is one comma-joined string; the picker works on ids.
const pickedSites = computed<string[]>({
  get: () =>
    form.value.ft_sites
      .split(',')
      .map((site) => site.trim())
      .filter(Boolean),
  set: (picked) => {
    form.value.ft_sites = picked.join(', ')
  }
})
</script>

<template>
  <SettingsSection :title="_t('Folder tree')">
    <EditField
      :label="_t('Root folder')"
      :help="
        _t(
          'Show only this folder and below. Empty = whole tree. Accepts a folder path or its stable id.'
        )
      "
    >
      <CmkDropdown
        :model-value="form.ft_root_folder"
        :options="rootFolderOptions"
        :label="_t('Root folder')"
        width="fill"
        @update:model-value="form.ft_root_folder = $event ?? ''"
      />
    </EditField>

    <EditField
      :label="_t('Auto-expand depth')"
      :help="_t('How many folder levels are expanded when the map opens.')"
    >
      <CmkInput v-model="form.ft_default_expand_depth" type="number" min="0" max="20" />
    </EditField>

    <EditField
      :label="_t('Default view')"
      :help="_t('Which presentation the map opens in by default.')"
    >
      <CmkDropdown
        :model-value="form.ft_default_view"
        :options="defaultViewOptions"
        :label="_t('Default view')"
        width="fill"
        @update:model-value="form.ft_default_view = ($event as 'list' | 'map') ?? 'list'"
      />
    </EditField>

    <EditField
      :label="_t('Sites')"
      :help="
        _t('Distributed monitoring: limit the tree to these sites. None selected = all sites.')
      "
    >
      <FolderTreeSitesSelect v-model="pickedSites" :options="sites" />
    </EditField>

    <div class="maps-folder-tree-settings__toggles">
      <!-- .stop on the switches: the slider toggles itself, and the wrapping
           label would forward a second click to the hidden checkbox. -->
      <label class="maps-folder-tree-settings__toggle">
        <CmkSwitch v-model="form.ft_show_empty_folders" @click.stop />
        <span>{{ _t('Show empty folders') }}</span>
      </label>
      <label class="maps-folder-tree-settings__toggle">
        <CmkSwitch v-model="form.ft_show_services" @click.stop />
        <span>{{ _t('Expand hosts to their services') }}</span>
      </label>
      <label class="maps-folder-tree-settings__toggle">
        <CmkSwitch v-model="form.ft_problems_only" @click.stop />
        <span>{{ _t('Show only folders/hosts with problems') }}</span>
      </label>
      <EditField
        v-if="form.ft_problems_only"
        :label="_t('Problem severity')"
        :help="
          _t(
            'On typical sites almost every host carries some WARNING service — narrowing to critical keeps the problem filter meaningful.'
          )
        "
      >
        <CmkDropdown
          :model-value="form.ft_problems_severity"
          :options="severityOptions"
          :label="_t('Problem severity')"
          width="fill"
          @update:model-value="form.ft_problems_severity = ($event as 'any' | 'critical') ?? 'any'"
        />
      </EditField>
      <label class="maps-folder-tree-settings__toggle">
        <CmkSwitch v-model="form.ft_only_hard_states" @click.stop />
        <span>{{ _t('Use hard states only') }}</span>
      </label>
    </div>
  </SettingsSection>
</template>

<style scoped>
.maps-folder-tree-settings__toggles {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.maps-folder-tree-settings__toggle {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  font-size: var(--font-size-normal);
  color: var(--font-color);
  cursor: pointer;
}
</style>
