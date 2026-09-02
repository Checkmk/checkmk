<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The map list's own page header: what this page is, and what can be done to the
list as a whole.

``maps.py`` renders no heading and no page menu (see cmk/maps/gui/_pages.py) --
the SPA routes between the list, a map and the image library client side, and
server chrome cannot follow that. So the app owns its chrome, the way the
dashboard does.

Creating and importing a map are the two actions this page exists for, so they
are buttons. The image library and the two settings forms are administration
and are reached often enough to need a way in, rarely enough not to spend the
bar's width on -- they sit in the overflow menu.
-->
<script setup lang="ts">
import CmkBreadcrumb from 'cmk-ui-library/components/CmkBreadcrumb'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { DropdownMenuItem } from 'reka-ui'

import { useAuth, useNavigation } from '@/maps/services/context'
import { useMapsBreadcrumbRoot } from '@/maps/shared/breadcrumb'
import MapsOverflowMenu from '@/maps/shared/components/MapsOverflowMenu.vue'
import { useMapsPageLinks } from '@/maps/shared/pageLinks'

const emit = defineEmits<{
  create: []
  import: []
}>()

const { _t } = usei18n()
const auth = useAuth()
const nav = useNavigation()
const links = useMapsPageLinks()

// The list is where the SPA starts, so its own level is the last one: below it
// the views route client side and carry their breadcrumb themselves.
const breadcrumb = [...useMapsBreadcrumbRoot(), { title: _t('Maps'), link: null }]
</script>

<template>
  <div class="maps-map-list-header">
    <CmkBreadcrumb :items="breadcrumb" />

    <div class="maps-map-list-header__bar">
      <CmkHeading type="h2">{{ _t('Maps') }}</CmkHeading>

      <div class="maps-map-list-header__actions">
        <template v-if="auth.canCreateMaps.value">
          <CmkButton
            variant="secondary"
            :icon="{ name: 'upload', size: 'small' }"
            @click="emit('import')"
          >
            {{ _t('Import') }}
          </CmkButton>
          <CmkButton
            variant="primary"
            :icon="{ name: 'new', size: 'small' }"
            @click="emit('create')"
          >
            {{ _t('Add map') }}
          </CmkButton>
        </template>

        <MapsOverflowMenu v-if="auth.canConfigure.value" :label="_t('Maps administration')">
          <DropdownMenuItem
            class="maps-overflow-menu__item"
            @select="nav.navigate({ view: 'admin', tab: 'icons' })"
          >
            {{ _t('Images') }}
          </DropdownMenuItem>
          <!-- Checkmk pages, not SPA views: a full navigation out of the app. -->
          <DropdownMenuItem as-child class="maps-overflow-menu__item">
            <a :href="links.authoring_settings">{{ _t('Map & object defaults') }}</a>
          </DropdownMenuItem>
          <DropdownMenuItem as-child class="maps-overflow-menu__item">
            <a :href="links.daemon_settings">{{ _t('Connections & daemon') }}</a>
          </DropdownMenuItem>
        </MapsOverflowMenu>
      </div>
    </div>
  </div>
</template>

<style scoped>
.maps-map-list-header {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-bottom: var(--dimension-6);
}

.maps-map-list-header__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-6);
}

.maps-map-list-header__actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
