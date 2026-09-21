"""Strip secrets and production residue from vendored pipeline files.

Scripted rather than done by hand so that the diff is reproducible and a
reviewer can check what was removed. The security design of the original
pipeline is described in the report as a methods point. Its hosts, credential
ids and run residue are not.
"""

import copy
import re
from pathlib import PurePosixPath
from typing import Any, Mapping

PLACEHOLDER_HOST = "example.invalid"
PLACEHOLDER_IP = "0.0.0.0"

# The subdomain is optional: the bare zone appears in a source comment
# ("both under axl-lvy.fr, DNS we own"), which a subdomain-only pattern misses.
_PRIVATE_DOMAIN = re.compile(r"\b(?:[a-z0-9-]+\.)*axl-lvy\.fr\b", re.I)

# Each branch must consume all four octets. Writing the shared tail once, as
# `(?:192\.168|10|100\....)\.\d{1,3}\.\d{1,3}`, gives the 10/8 branch only
# three octets, so `10.0.0.5` matches `10.0.0` and leaves a stray `.5` behind.
_PRIVATE_IPV4 = re.compile(
    r"\b(?:"
    r"10(?:\.\d{1,3}){3}"
    r"|192\.168(?:\.\d{1,3}){2}"
    r"|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])(?:\.\d{1,3}){2}"
    r")\b"
)

# A whitelist, not a blacklist: an n8n export carries instance state that has
# grown between versions (activeVersionId, sourceWorkflowId, versionCounter,
# versionMetadata, createdAt, triggerCount, tags), and a blacklist would leak
# whatever the next version adds. Only the four keys that carry the method
# survive, plus the node groups for their documentation.
_KEEP_TOP_LEVEL = ("name", "description", "nodes", "connections", "settings")
_DROP_SETTINGS = ("errorWorkflow", "callerPolicy")
_DROP_NODE = ("webhookId", "id")
# A node group is a caption over a set of nodes. Its wording documents the
# pipeline and is kept; its own id and its node ids are editor identifiers.
_KEEP_NODE_GROUP = ("name", "description")


def scrub_text(text: str) -> str:
    """Replace private hostnames and addresses with placeholders.

    Container names on the private docker network (`ocr`, `ollama`, `n8n`) are
    left alone: they are not secrets, and the report describes that service
    graph.
    """
    out = _PRIVATE_DOMAIN.sub(PLACEHOLDER_HOST, text)
    return _PRIVATE_IPV4.sub(PLACEHOLDER_IP, out)


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub(item) for key, item in value.items()}
    return value


def sanitise_workflow(document: dict) -> dict:
    """Return a copy of an n8n workflow export that is safe to publish."""
    out = {
        key: copy.deepcopy(value)
        for key, value in document.items()
        if key in _KEEP_TOP_LEVEL
    }

    groups = document.get("nodeGroups")
    if isinstance(groups, list):
        kept = [
            {k: v for k, v in group.items() if k in _KEEP_NODE_GROUP}
            for group in groups
            if isinstance(group, dict)
        ]
        if kept:
            out["nodeGroups"] = kept

    settings = out.get("settings")
    if isinstance(settings, dict):
        for key in _DROP_SETTINGS:
            settings.pop(key, None)

    for node in out.get("nodes", []):
        if not isinstance(node, dict):
            continue
        for key in _DROP_NODE:
            node.pop(key, None)
        credentials = node.get("credentials")
        if isinstance(credentials, dict):
            for slot, detail in credentials.items():
                if isinstance(detail, dict):
                    credentials[slot] = {
                        k: v for k, v in detail.items() if k == "name"
                    }

    return _scrub(out)


#: The only fields in an OCR run record that hold a filesystem path. Everything
#: else the harness wrote is a count, a flag or a note about the page. Audited
#: over all 48 recovered files: no other value contains an absolute path.
_PATH_FIELDS = ("input", "outDir", "model", "out")


def scrub_run_paths(record: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce a run record's absolute paths to their basenames.

    The basename is the whole of what the method needs: which source PDF was
    read and which fine-tuned model read it. The directories above it say where
    one person's machine keeps its corpus and that the model came off a private
    home-lab checkout, which is run residue rather than method.

    Only the four known path fields are touched, so a field added by a later
    harness version arrives unscrubbed and visible rather than silently
    rewritten.
    """
    out = dict(record)
    for field_name in _PATH_FIELDS:
        value = out.get(field_name)
        if isinstance(value, str) and value:
            out[field_name] = PurePosixPath(value).name
    return out
