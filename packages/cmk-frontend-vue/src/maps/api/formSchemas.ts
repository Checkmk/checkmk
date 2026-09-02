/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * FormSpec schemas for the dialogs the SPA renders with ``FormEdit``, and the
 * translation of their values.
 *
 * Serialising a FormSpec needs a full GUI request and the authenticated user (a
 * Password field lists that user's password store), so this is served by the
 * GUI process rather than the daemon.
 *
 * The values go the same way, because a form's data bag is not what gets
 * stored: a single-choice field carries an opaque id per element, and only the
 * form spec on the server knows which stored value each one stands for. So a
 * dialog asks the server to encode its stored values when it opens
 * (``fetch``) and to decode the edited ones when it saves (``parse``), rather
 * than reading its own bag.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import type { ValidationMessage } from 'cmk-shared-typing/typescript/vue_formspec_components'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

/** The dialogs that are rendered from a server-side FormSpec. */
export type FormSchemaName = 'map_metadata' | 'map_bulk_metadata' | 'flow_view'

/** A form spec's schema together with its values, as the form wants them. */
export type FormSchemaAndData = components['schemas']['MapsFormSchemaResponse']

/**
 * Decoded values, or what the form spec objected to. The dialogs render
 * ``validation`` through ``FormEdit``'s ``backend-validation``, so a rejected
 * value is reported on the field that carries it.
 */
export type FormParseResult =
  | { data: Record<string, unknown>; validation?: undefined }
  | { data?: undefined; validation: ValidationMessage[] }

export class FormSchemaApi {
  /**
   * The schema plus the values to prefill it with. ``stored`` holds them in
   * their stored form; leaving it out renders the form spec's own prefills,
   * which is what an empty bulk-edit dialog wants.
   */
  public async fetch(
    spec: FormSchemaName,
    stored?: Record<string, unknown>
  ): Promise<FormSchemaAndData> {
    return unwrap(
      await client.POST('/objects/maps_form/{spec}/actions/schema/invoke', {
        params: { path: { spec }, header: { 'Content-Type': 'application/json' } },
        body: stored === undefined ? {} : { data: stored }
      })
    )
  }

  /** The edited bag as it is stored — the values to send to the Maps API. */
  public async parse(
    spec: FormSchemaName,
    values: Record<string, unknown>
  ): Promise<FormParseResult> {
    const result = unwrap(
      await client.POST('/objects/maps_form/{spec}/actions/parse/invoke', {
        params: { path: { spec }, header: { 'Content-Type': 'application/json' } },
        body: { data: values }
      })
    )
    return result.validation === undefined
      ? { data: result.data ?? {} }
      : { validation: result.validation as ValidationMessage[] }
  }
}
