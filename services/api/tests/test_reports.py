from app.api.v1.reports import safe_spreadsheet_value


def test_spreadsheet_values_neutralize_formula_injection() -> None:
    assert safe_spreadsheet_value("=HYPERLINK(\"https://example.invalid\")") == (
        "'=HYPERLINK(\"https://example.invalid\")"
    )
    assert safe_spreadsheet_value("  +SUM(1,2)") == "'  +SUM(1,2)"
    assert safe_spreadsheet_value("@malicious") == "'@malicious"
    assert safe_spreadsheet_value("Normal task") == "Normal task"
    assert safe_spreadsheet_value(42) == 42
