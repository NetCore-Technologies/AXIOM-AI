# AXIOM Model Registry

The Control Center's **Models** page reads from the local AXIOM model registry. Registry actions operate on metadata; removing a registry record does not delete the model's weight files.

## Search, filter, sort, and paginate

The Models page provides server-side inventory controls:

- **Search metadata** performs a case-insensitive substring search across name, source, format, parameter metadata, quantization, architecture, licence, and tags.
- **Exact format** matches the format label case-insensitively, such as gguf or safetensors.
- **Exact tag** matches an entire tag label case-insensitively; it does not match a partial tag.
- **Favorites only** limits results to records marked as favorites.
- **Sort by** supports name, source, format, parameters, quantization, and favorite status. Text ordering is case-insensitive. Parameter strings such as 1.5B, 7B, and 13B are ordered numerically; records with missing or unparseable parameter metadata remain last in either direction.
- **Order** selects ascending or descending results.
- **Load more models** fetches the next page using the same applied filter and sorting state. The API filters and sorts the complete registry before applying the page offset, so page totals and has_more refer to the filtered result set.

The API endpoint is GET /api/workspace/models. Its optional query parameters are search, favorite_only, format, tag, sort_by, and sort_order, alongside the existing bounded limit and offset. Results include the filtered total, selected limit and offset, and boolean has_more.

## Saved filters and privacy

Saved filter presets are stored in this browser's local storage under a versioned AXIOM key. Each preset contains only its name and filter options, not model weights, credentials, prompts, or model files. Up to 20 presets are retained. Clearing the filter form does not delete saved presets; each preset can be applied or deleted explicitly.

Registry contents and search requests still go to the local AXIOM API. A saved preset is a convenience for this browser, not a cross-device account setting or server-side shared preference.

## Validation boundary

Automated Python API tests cover case-insensitive search, exact filters, numeric parameter sorting, unknown-size ordering, invalid sort fields, and pagination after filtering. Playwright coverage exercises the GUI query contract and saved-preset interaction. Treat this roadmap work as in progress until CI reports the complete Python, lint, production-build, and browser test suite passing.
