import pytest

from app.frontend.exports.batch_export_view_builder import BatchExportViewBuilder


@pytest.mark.parametrize("kind,label", [
    ("unresolved_numeric_sequence", "Sequência numérica inconclusiva"),
    ("payment_line_candidate", "Candidata de pagamento — vínculo não confirmado"),
    ("concatenated_fields", "Observação numérica — campos concatenados"),
])
def test_location_label_does_not_promote_uncertain_sequence_to_payment_line(kind, label):
    [record] = BatchExportViewBuilder()._build_locations([{
        "id": "example", "filename": "document.pdf",
        "numeric_line_locations": [{"line_index": 1, "located": True}],
        "numeric_line_validations": [{"line_index": 1, "contextual_kind": kind}],
    }])
    assert record["location_type_label"] == label
