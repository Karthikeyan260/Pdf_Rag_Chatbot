from app.services.retrieval.merge import reciprocal_rank_fusion


def test_fuses_agreeing_lists_higher():
    dense = ["a", "b", "c"]
    bm25 = ["a", "c", "b"]
    fused = reciprocal_rank_fusion([dense, bm25])
    fused_ids = [item_id for item_id, _ in fused]
    assert fused_ids[0] == "a"  # ranked first in both lists
    assert set(fused_ids) == {"a", "b", "c"}


def test_id_present_in_only_one_list_still_included():
    fused = reciprocal_rank_fusion([["x", "y"], ["z"]])
    assert {item_id for item_id, _ in fused} == {"x", "y", "z"}


def test_empty_lists_produce_empty_result():
    assert reciprocal_rank_fusion([[], []]) == []
