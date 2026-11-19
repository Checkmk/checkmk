/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref } from 'vue'

import type { HostNameTemplateResolution } from './definition'
import type { TemplatePreview } from './templatePreview'

export type CreatableFolder = HostNameTemplateResolution['creatable_folders'][number]

/** The folder path each host that saving creates goes to, by host name. */
export type NewHostFolders = Record<string, string>

const MAIN_FOLDER = '/'

export function defaultFolder(folders: CreatableFolder[]): string | null {
  return folders.some((folder) => folder.path === MAIN_FOLDER)
    ? MAIN_FOLDER
    : (folders[0]?.path ?? null)
}

/**
 * The folder of every host the template preview names as new: the one chosen for it while it is
 * still offered, else the default. Empty until the preview has resolved.
 */
export function newHostFoldersOf(chosen: NewHostFolders, preview: TemplatePreview): NewHostFolders {
  if (preview.status !== 'resolved') {
    return {}
  }
  const { creatable_folders: folders, unmatched_host_names: hostNames } = preview.resolution
  const fallback = defaultFolder(folders)
  if (fallback === null) {
    return {}
  }
  const offered = new Set(folders.map((folder) => folder.path))
  return Object.fromEntries(
    hostNames.map((hostName) => {
      const choice = chosen[hostName]
      return [hostName, choice !== undefined && offered.has(choice) ? choice : fallback]
    })
  )
}

/** The folders to send: the endpoint creates a host it is not told about in Main. */
export function newHostFoldersToSend(folders: NewHostFolders): NewHostFolders {
  return Object.fromEntries(Object.entries(folders).filter(([, path]) => path !== MAIN_FOLDER))
}

export interface NewHostFolderChoice {
  folders: Readonly<Ref<NewHostFolders>>
  toSend: Readonly<Ref<NewHostFolders>>
  choose: (hostNames: string[], folder: string) => void
}

/** The folders of the new hosts, kept by host name while the template preview changes. */
export function useNewHostFolders(getPreview: () => TemplatePreview): NewHostFolderChoice {
  const chosen = ref<NewHostFolders>({})
  const folders = computed(() => newHostFoldersOf(chosen.value, getPreview()))
  return {
    folders,
    toSend: computed(() => newHostFoldersToSend(folders.value)),
    choose(hostNames, folder) {
      chosen.value = {
        ...chosen.value,
        ...Object.fromEntries(hostNames.map((hostName) => [hostName, folder]))
      }
    }
  }
}
