from app.services.evaluator import EvaluatorService

def test_evaluator_metrics_calculation():
    evaluator = EvaluatorService()
    
    # Test word overlap similarity
    sim = evaluator.compute_word_overlap_similarity("Return items within 30 days", "30 days return policy")
    assert sim > 0.3

    # Test simulated benchmark calculation
    results = evaluator.run_full_evaluation()
    assert "hit_rate_at_1" in results
    assert "hit_rate_at_5" in results
    assert "mrr" in results
    assert "faithfulness" in results
    assert results["hit_rate_at_1"] >= 0.0
