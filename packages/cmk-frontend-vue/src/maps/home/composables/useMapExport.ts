/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import { useMaps, useToast } from '@/maps/services/context'
import { errorText } from '@/maps/shared/errorText'

/**
 * Taking a map out of the site as a JSON file.
 *
 * Downloading is a browser concern, not an API one: the config comes from the
 * map service, the file is produced here.
 */
export function useMapExport(): { exportMap: (name: string) => Promise<void> } {
  const maps = useMaps()
  const toast = useToast()
  const { _t } = usei18n()

  async function exportMap(name: string): Promise<void> {
    let config
    try {
      config = await maps.getMap(name)
    } catch (error: unknown) {
      toast.error(errorText(error, _t('Export failed')))
      return
    }
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
    )
    const link = document.createElement('a')
    link.href = url
    link.download = `${name}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  return { exportMap }
}
