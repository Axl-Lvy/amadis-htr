# Sanitisation

Files under `pipeline/` are copies of code from a private repository. They are
passed through `src/amadis_htr/sanitise.py` before being committed, so that the
removal is reproducible and reviewable rather than a manual pass.

## Whitelist, not blacklist

The workflow export carries instance state that has grown between n8n versions:
`activeVersionId`, `sourceWorkflowId`, `versionCounter`, `versionMetadata`,
`createdAt`, `updatedAt`, `triggerCount`, `isArchived`, `active`, `tags`. A
blacklist would have published whatever the next version adds. Only the keys
that carry the method survive: `name`, `description`, `nodes`, `connections`,
`settings`, plus the node-group captions.

## What is removed

| removed | why |
|---|---|
| `staticData` | residue of a real 348-page production run: transcribed text, job id, run id, callback URL. 480 KB of the original 488 KB file. |
| every top-level key outside the whitelist | instance state and version identifiers, not pipeline logic |
| node `webhookId` and `id` | a live webhook path and editor identifiers |
| node-group `id` and `nodeIds` | editor identifiers. The group's `name` and `description` are kept, because they caption the pipeline and document it. |
| `settings.errorWorkflow`, `settings.callerPolicy` | identifiers of a live workflow |
| credential `id` | the credential's **name** is kept, so the report can say which node authenticates how |
| hosts under the private DNS zone | replaced with `example.invalid` |
| private IPv4 addresses | replaced with `0.0.0.0` |

## What is deliberately kept

Container names on the private docker network (`ocr`, `ollama`, `n8n`) stay,
because the report describes that service graph and the names are not secrets.

Every prompt, threshold, model name and Code node stays. Those are the method.
In particular `sd.amadisPrev` appears in four Code nodes: that is the lag-1
coherence buffer, and only the `staticData` payload it produced was residue.

## One thing the scrubbing loses

The production and preview hostnames are two distinct values and both become
`example.invalid`, so the callback allowlist in the `Validate` Code node reads
`["example.invalid", "example.invalid"]`. The report quotes that block, so its
caption says two distinct hosts collapsed to one placeholder. The mechanism
being described is that an exact-match allowlist exists at all, not what is in
it.

## How to re-check

```sh
grep -c 'axl-lvy\|staticData\|webhookId' pipeline/n8n/amadis-ocr.json
grep -coE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' \
  pipeline/n8n/amadis-ocr.json
```

Expect no matches from either.
