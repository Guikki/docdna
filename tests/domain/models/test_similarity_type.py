from app.domain.models.similarity_type import SimilarityType


def test_all_similarity_types_have_string_values():
    for similarity in SimilarityType:
        assert isinstance(similarity.value, str)


def test_all_similarity_types_have_display_name():
    for similarity in SimilarityType:
        assert similarity.display_name != ""


def test_all_similarity_types_have_icon():
    for similarity in SimilarityType:
        assert similarity.icon != ""


def test_all_similarity_types_have_frontend_color():
    for similarity in SimilarityType:
        assert similarity.frontend_color != ""


def test_text_similarity():
    assert SimilarityType.TEXT.value == "text"
    assert SimilarityType.TEXT.display_name == "Texto"


def test_barcode_similarity():
    assert SimilarityType.BARCODE.display_name == "Código de barras"


def test_temporal_similarity():
    assert SimilarityType.TEMPORAL.display_name == "Datas"


def test_visual_similarity():
    assert SimilarityType.VISUAL.display_name == "Similaridade visual"