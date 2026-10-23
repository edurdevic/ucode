"""Tests for the request-tags header helper shared by agent launchers."""

from __future__ import annotations

import json

from ucode.agents.request_tags import request_tags_header_value


class TestRequestTagsHeaderValue:
    def test_returns_stripped_value_from_explicit_env(self, tmp_path):
        env = {"AI_GATEWAY_REQUEST_TAGS": '  {"source":"my-app"}  '}
        assert request_tags_header_value(env, cwd=tmp_path) == '{"source":"my-app"}'

    def test_returns_none_when_absent(self, tmp_path):
        assert request_tags_header_value({}, cwd=tmp_path) is None

    def test_returns_none_when_blank(self, tmp_path):
        assert request_tags_header_value({"AI_GATEWAY_REQUEST_TAGS": "   "}, cwd=tmp_path) is None

    def test_reads_process_environment_by_default(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AI_GATEWAY_REQUEST_TAGS", '{"source":"my-app"}')
        assert request_tags_header_value(cwd=tmp_path) == '{"source":"my-app"}'

    def test_process_environment_unset_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AI_GATEWAY_REQUEST_TAGS", raising=False)
        assert request_tags_header_value(cwd=tmp_path) is None

    def test_skips_and_warns_on_embedded_newline(self, capsys, tmp_path):
        pretty_json = '{\n  "source": "my-app"\n}'
        assert (
            request_tags_header_value({"AI_GATEWAY_REQUEST_TAGS": pretty_json}, cwd=tmp_path)
            is None
        )
        err = capsys.readouterr().err
        assert "AI_GATEWAY_REQUEST_TAGS" in err
        assert "line breaks" in err

    def test_skips_and_warns_on_carriage_return(self, capsys, tmp_path):
        value = '{"a":"b"}\r{"c":"d"}'
        assert request_tags_header_value({"AI_GATEWAY_REQUEST_TAGS": value}, cwd=tmp_path) is None
        assert "AI_GATEWAY_REQUEST_TAGS" in capsys.readouterr().err

    def test_skips_and_warns_on_invalid_json(self, capsys, tmp_path):
        value = '{"a":"b"'
        assert request_tags_header_value({"AI_GATEWAY_REQUEST_TAGS": value}, cwd=tmp_path) is None
        assert "AI_GATEWAY_REQUEST_TAGS" in capsys.readouterr().err

    def test_skips_and_warns_on_non_object_json(self, capsys, tmp_path):
        value = '"A string!"'
        assert request_tags_header_value({"AI_GATEWAY_REQUEST_TAGS": value}, cwd=tmp_path) is None
        assert "AI_GATEWAY_REQUEST_TAGS" in capsys.readouterr().err


class TestProjectRequestTagsFile:
    @staticmethod
    def _write_project_file(tmp_path, content: str) -> None:
        project_dir = tmp_path / ".ucode"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "request-tags.json").write_text(content, encoding="utf-8")

    def test_returns_none_when_file_missing(self, tmp_path):
        assert request_tags_header_value({}, cwd=tmp_path) is None

    def test_used_as_default_when_env_unset(self, tmp_path):
        self._write_project_file(tmp_path, '{"project":"p-1042"}')
        assert request_tags_header_value({}, cwd=tmp_path) == '{"project":"p-1042"}'

    def test_used_as_default_when_env_blank(self, tmp_path):
        self._write_project_file(tmp_path, '{"project":"p-1042"}')
        assert (
            request_tags_header_value({"AI_GATEWAY_REQUEST_TAGS": "   "}, cwd=tmp_path)
            == '{"project":"p-1042"}'
        )

    def test_env_var_takes_precedence_over_project_file(self, tmp_path):
        self._write_project_file(tmp_path, '{"project":"p-1042"}')
        env = {"AI_GATEWAY_REQUEST_TAGS": '{"source":"my-app"}'}
        assert request_tags_header_value(env, cwd=tmp_path) == '{"source":"my-app"}'

    def test_reads_process_working_directory_by_default(self, monkeypatch, tmp_path):
        self._write_project_file(tmp_path, '{"project":"p-1042"}')
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AI_GATEWAY_REQUEST_TAGS", raising=False)
        assert request_tags_header_value() == '{"project":"p-1042"}'

    def test_compacts_pretty_printed_json_onto_a_single_line(self, tmp_path):
        pretty_json = '{\n  "project": "p-1042",\n  "team": "field-eng"\n}'
        self._write_project_file(tmp_path, pretty_json)
        value = request_tags_header_value({}, cwd=tmp_path)
        assert value is not None
        assert "\n" not in value
        assert json.loads(value) == {"project": "p-1042", "team": "field-eng"}

    def test_returns_none_when_file_is_blank(self, tmp_path):
        self._write_project_file(tmp_path, "   ")
        assert request_tags_header_value({}, cwd=tmp_path) is None

    def test_skips_and_warns_on_invalid_json(self, capsys, tmp_path):
        self._write_project_file(tmp_path, '{"project":')
        assert request_tags_header_value({}, cwd=tmp_path) is None
        err = " ".join(capsys.readouterr().err.split())
        assert "request-tags.json" in err
        assert "not valid JSON" in err

    def test_skips_and_warns_on_non_object_json(self, capsys, tmp_path):
        self._write_project_file(tmp_path, '"A string!"')
        assert request_tags_header_value({}, cwd=tmp_path) is None
        err = " ".join(capsys.readouterr().err.split())
        assert "request-tags.json" in err
        assert "expected a JSON object" in err
