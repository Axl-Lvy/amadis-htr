import json

from amadis_htr.sanitise import sanitise_workflow, scrub_text


def test_static_data_is_removed_entirely():
    doc = {"name": "amadis-ocr", "staticData": {"global": {"amadisPrev": "..."}}}
    assert "staticData" not in sanitise_workflow(doc)


def test_credential_ids_are_removed_but_the_name_is_kept():
    doc = {
        "nodes": [
            {
                "name": "Webhook",
                "credentials": {"httpHeaderAuth": {"id": "FMANBA54S8FhsGYe",
                                                   "name": "OCR Webhook"}},
            }
        ]
    }
    node = sanitise_workflow(doc)["nodes"][0]
    assert node["credentials"]["httpHeaderAuth"] == {"name": "OCR Webhook"}


def test_webhook_id_is_removed():
    doc = {"nodes": [{"name": "Webhook", "webhookId": "53437b11-ecc6-4451-97b0"}]}
    assert "webhookId" not in sanitise_workflow(doc)["nodes"][0]


def test_workflow_and_version_ids_are_removed():
    doc = {"id": "Q9jEMd6zCv9stSvV", "versionId": "81319df6", "name": "amadis-ocr"}
    out = sanitise_workflow(doc)
    assert "id" not in out and "versionId" not in out
    assert out["name"] == "amadis-ocr"


def test_error_workflow_id_is_removed_from_settings():
    doc = {"settings": {"executionOrder": "v1", "errorWorkflow": "fDYSwKxnDbeWDBka"}}
    settings = sanitise_workflow(doc)["settings"]
    assert settings == {"executionOrder": "v1"}


def test_hostnames_inside_node_parameters_are_scrubbed():
    doc = {
        "nodes": [
            {
                "name": "Validate",
                "parameters": {
                    "jsCode": 'const HOSTS = ["amadis.axl-lvy.fr", "amadis-preview.axl-lvy.fr"];'
                },
            }
        ]
    }
    code = sanitise_workflow(doc)["nodes"][0]["parameters"]["jsCode"]
    assert "axl-lvy.fr" not in code
    assert "example.invalid" in code


def test_scrub_replaces_every_private_host_form():
    text = (
        "https://amadis.axl-lvy.fr/api/ocr/callback\n"
        "https://ntfy.axl-lvy.fr/n8n-errors\n"
        "http://ollama:11434/api/chat/\n"
        "192.168.1.66 and 100.94.250.14 and 10.0.0.5\n"
    )
    out = scrub_text(text)
    assert "axl-lvy.fr" not in out
    assert "192.168.1.66" not in out
    assert "100.94.250.14" not in out
    assert "10.0.0.5" not in out
    # Every branch must eat all four octets. A three-octet match would leave a
    # stray ".5" behind and look like it had worked.
    assert "0.0.0.0 and 0.0.0.0 and 0.0.0.0" in out
    # Container names on a private docker network are not secrets and stay,
    # because the report describes the service graph.
    assert "http://ollama:11434/api/chat/" in out


def test_a_version_number_is_not_mistaken_for_an_address():
    assert scrub_text("kraken 10.5 and torch 2.10.0") == "kraken 10.5 and torch 2.10.0"


def test_scrubbing_is_idempotent():
    once = scrub_text("https://amadis.axl-lvy.fr/x")
    assert scrub_text(once) == once


def test_a_pinned_sample_round_trips_through_json():
    doc = {"name": "amadis-ocr", "staticData": {"global": {}}, "nodes": []}
    assert json.loads(json.dumps(sanitise_workflow(doc))) == {"name": "amadis-ocr",
                                                              "nodes": []}


def test_the_bare_private_zone_in_a_comment_is_scrubbed():
    # The allowlist comment says "both under axl-lvy.fr, DNS we own", with no
    # subdomain, which a subdomain-only pattern walks straight past.
    assert "axl-lvy" not in scrub_text("// (both under axl-lvy.fr, DNS we own)")


def test_instance_state_is_dropped_by_whitelist_not_blacklist():
    doc = {
        "name": "amadis-ocr",
        "nodes": [],
        "connections": {},
        "activeVersionId": "81319df6-7d52-4f02-8890-c0cd4cc4070f",
        "sourceWorkflowId": "abc",
        "versionCounter": 139,
        "versionMetadata": {"name": "Version 81319df6"},
        "createdAt": "2026-07-06T19:30:19.513Z",
        "updatedAt": "2026-09-07T13:48:09.635Z",
        "triggerCount": 1,
        "isArchived": False,
        "active": True,
        "tags": [],
        "somethingAFutureVersionAdds": "leak",
    }
    out = sanitise_workflow(doc)
    assert set(out) == {"name", "nodes", "connections"}


def test_node_group_captions_survive_without_their_identifiers():
    doc = {
        "name": "amadis-ocr",
        "nodeGroups": [
            {
                "id": "35e6c558-76a2-4cd0-80f8-0669fdbf11cb",
                "name": "Error handling",
                "description": "Send call back + notification",
                "nodeIds": ["05f77296-ddcd-4ef7-ba9e-a87b32fdb8ba"],
            }
        ],
    }
    groups = sanitise_workflow(doc)["nodeGroups"]
    assert groups == [
        {"name": "Error handling", "description": "Send call back + notification"}
    ]


def test_code_node_source_is_never_touched():
    # `sd.amadisPrev` is the lag-1 coherence buffer, which is the method. Only
    # the staticData payload it produced is residue.
    code = "const sd = $getWorkflowStaticData('global');\nsd.amadisPrev = cur;"
    doc = {"name": "x", "nodes": [{"name": "Prep coherence",
                                   "parameters": {"jsCode": code}}]}
    assert sanitise_workflow(doc)["nodes"][0]["parameters"]["jsCode"] == code
