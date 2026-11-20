"""Último valor usado de los parámetros de una etapa (parametros.json)."""

from core.parameters import save_parameters, saved_parameters
from stages import stage_01_ety_cleaning, stage_04_payment_detail


def test_without_file_the_default_value_is_proposed(tmp_path):
    path = tmp_path / "parametros.json"
    assert saved_parameters(stage_04_payment_detail, path) == {"current_pac": "PAC JULIO 2026"}


def test_the_last_value_used_is_proposed(tmp_path):
    path = tmp_path / "parametros.json"
    save_parameters(stage_04_payment_detail, {"current_pac": " PAC NOVIEMBRE  2026 "}, path)
    assert saved_parameters(stage_04_payment_detail, path) == {"current_pac": "PAC NOVIEMBRE 2026"}
    assert "Ñ" not in path.read_text(encoding="utf-8")   # Se guarda como texto legible (UTF-8)


def test_damaged_file_or_empty_value_falls_back_to_the_default(tmp_path):
    path = tmp_path / "parametros.json"
    path.write_text("{esto no es json", encoding="utf-8")
    assert saved_parameters(stage_04_payment_detail, path) == {"current_pac": "PAC JULIO 2026"}
    path.write_text('{"E04_payment_detail": {"current_pac": "  "}}', encoding="utf-8")
    assert saved_parameters(stage_04_payment_detail, path) == {"current_pac": "PAC JULIO 2026"}


def test_values_of_other_stages_are_kept(tmp_path):
    path = tmp_path / "parametros.json"
    path.write_text('{"E09_other": {"x": "1"}}', encoding="utf-8")
    save_parameters(stage_04_payment_detail, {"current_pac": "PAC ENERO 2027"}, path)
    assert '"E09_other"' in path.read_text(encoding="utf-8")


def test_stage_without_parameters(tmp_path):
    path = tmp_path / "parametros.json"
    assert saved_parameters(stage_01_ety_cleaning, path) == {}
    save_parameters(stage_01_ety_cleaning, {}, path)
    assert not path.exists()
