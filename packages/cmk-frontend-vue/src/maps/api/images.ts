/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The image library.
 *
 * GUI-owned: the files are written under the site and served statically by
 * Apache, so everything here goes through Checkmk's internal REST API.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { uploadedFile } from '@/maps/api/upload'
import type { ImageEntry, ImageUsageEntry } from '@/maps/types/api'

/** The maps an in-use image is still referenced by, off a refused delete. */
function blockingUsage(error: unknown): ImageUsageEntry[] | null {
  if (!(error instanceof CmkApiError) || error.statusCode !== 409) {
    return null
  }
  const usage = (error.body as { ext?: { usage?: ImageUsageEntry[] } } | undefined)?.ext?.usage
  return usage ?? []
}

export class ImagesApi {
  public async list(): Promise<ImageEntry[]> {
    return unwrap(await client.GET('/domain-types/maps_image/collections/all')).images
  }

  public async upload(file: File): Promise<ImageEntry> {
    return unwrap(
      await client.POST('/domain-types/maps_image/collections/all', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: await uploadedFile(file)
      })
    )
  }

  public async usage(name: string): Promise<ImageUsageEntry[]> {
    return unwrap(
      await client.GET('/objects/maps_image/{name}/actions/usage/invoke', {
        params: { path: { name } }
      })
    ).usage
  }

  /**
   * Deletes an image, and returns the maps still referencing it when it was kept.
   *
   * Without ``force`` an image in use is refused with a 409 carrying those maps,
   * so the SPA can show what would break and ask again. An empty list means the
   * image is gone.
   */
  public async delete(name: string, force = false): Promise<ImageUsageEntry[]> {
    try {
      unwrap(
        await client.DELETE('/objects/maps_image/{name}', {
          // Query parameters cross the wire as text; the endpoint parses the flag.
          params: { path: { name }, query: { force: String(force) } }
        })
      )
      return []
    } catch (error: unknown) {
      const blocking = blockingUsage(error)
      if (blocking === null) {
        throw error
      }
      return blocking
    }
  }
}
