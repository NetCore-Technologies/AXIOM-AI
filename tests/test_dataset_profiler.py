import json

from axiom.datasets.profiler import profile_jsonl


def test_profile_counts_rows_duplicates_and_types(tmp_path):
    source = tmp_path / "train.jsonl"
    source.write_text(
        '{"text":"hello","count":1}\n'
        '{"text":"hello","count":1}\n'
        '{"text":"world","count":null}\n'
        'not json\n'
        '\n',
        encoding="utf-8",
    )

    report = profile_jsonl(source)
    assert report["valid_rows"] == 3
    assert report["invalid_rows"] == 1
    assert report["empty_rows"] == 1
    assert report["duplicate_rows"] == 1
    fields = {field["name"]: field for field in report["fields"]}
    assert fields["count"]["null_count"] == 1
    assert fields["text"]["types"] == {"string": 3}


def test_profile_flags_sensitive_field_names_without_exposing_values(tmp_path):
    secret_value = "private-test-value-98765"
    source = tmp_path / "private.jsonl"
    source.write_text(json.dumps({"email": secret_value, "password_hash": "hash"}) + "\n", encoding="utf-8")

    report = profile_jsonl(source)
    rendered = json.dumps(report)
    assert report["privacy_review_recommended"] is True
    assert set(report["possibly_sensitive_fields"]) == {"email", "password_hash"}
    assert secret_value not in rendered


def test_profile_enforces_byte_and_line_limits(tmp_path):
    source = tmp_path / "large.jsonl"
    source.write_text('{"text":"' + ('x' * 256) + '"}\n{"text":"later"}\n', encoding="utf-8")

    report = profile_jsonl(source, max_bytes=32, max_rows=100, max_line_bytes=16)
    assert report["truncated"] is True
    assert report["bytes_scanned"] <= 32
    assert report["overlong_rows"] >= 1 or report["invalid_rows"] >= 1


def test_profile_rejects_invalid_limits_and_non_object_json(tmp_path):
    source = tmp_path / "mixed.jsonl"
    source.write_text('[1,2]\nnull\nNaN\n', encoding="utf-8")
    report = profile_jsonl(source)
    assert report["valid_rows"] == 0
    assert report["invalid_rows"] == 3

    try:
        profile_jsonl(source, max_rows=0)
    except ValueError as exc:
        assert "positive integers" in str(exc)
    else:
        raise AssertionError("invalid limit should be rejected")
