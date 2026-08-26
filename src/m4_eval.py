from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    zeros = {"faithfulness": 0.0, "answer_relevancy": 0.0,
             "context_precision": 0.0, "context_recall": 0.0, "per_question": []}
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset

        dataset = Dataset.from_dict({
            "question": questions, "answer": answers,
            "contexts": contexts, "ground_truth": ground_truths,
        })
        result = evaluate(dataset, metrics=[faithfulness, answer_relevancy,
                                             context_precision, context_recall])
        df = result.to_pandas()

        def _clean(v) -> float:
            """RAGAS trả NaN khi 1 row bị lỗi parse/generation — không để NaN
            lan ra toàn bộ average (sum/len với NaN → NaN)."""
            try:
                v = float(v)
            except (TypeError, ValueError):
                return 0.0
            return 0.0 if v != v else v  # v != v chỉ đúng khi v là NaN

        per_question = [
            EvalResult(question=row["question"], answer=row["answer"],
                       contexts=list(row["contexts"]), ground_truth=row["ground_truth"],
                       faithfulness=_clean(row.get("faithfulness", 0.0)),
                       answer_relevancy=_clean(row.get("answer_relevancy", 0.0)),
                       context_precision=_clean(row.get("context_precision", 0.0)),
                       context_recall=_clean(row.get("context_recall", 0.0)))
            for _, row in df.iterrows()
        ]

        # Dùng result["metric_name"] (safe_nanmean nội bộ của ragas, bỏ qua NaN)
        # cho aggregate — chính xác hơn tự sum() trên per_question đã bị 0-hoá.
        # per_question vẫn giữ 0.0 cho row lỗi để failure_analysis() bắt được nó.
        return {
            "faithfulness": _clean(result.get("faithfulness", 0.0)),
            "answer_relevancy": _clean(result.get("answer_relevancy", 0.0)),
            "context_precision": _clean(result.get("context_precision", 0.0)),
            "context_recall": _clean(result.get("context_recall", 0.0)),
            "per_question": per_question,
        }
    except Exception as e:
        print(f"  ⚠️  RAGAS evaluation failed: {e}")
        return zeros


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating — answer không được context hỗ trợ đầy đủ",
                          "Tighten prompt (chỉ trả lời dựa context), lower temperature"),
        "context_recall": ("Missing relevant chunks — retriever không lấy đủ bằng chứng cần thiết",
                            "Improve chunking (giữ ngữ cảnh/section) hoặc tăng recall của BM25/dense"),
        "context_precision": ("Too many irrelevant chunks — context lẫn tài liệu không liên quan/sai version",
                               "Add reranking hoặc metadata filter theo source/version"),
        "answer_relevancy": ("Answer doesn't match question — câu trả lời lạc đề hoặc thiếu trọng tâm",
                              "Improve prompt template, ràng buộc trả lời đúng câu hỏi"),
    }

    scored = []
    for r in eval_results:
        metrics = {
            "faithfulness": r.faithfulness,
            "answer_relevancy": r.answer_relevancy,
            "context_precision": r.context_precision,
            "context_recall": r.context_recall,
        }
        avg = sum(metrics.values()) / len(metrics)
        worst_metric = min(metrics, key=metrics.get)
        scored.append((avg, worst_metric, metrics[worst_metric], r))

    scored.sort(key=lambda x: x[0])

    failures = []
    for avg, worst_metric, worst_score, r in scored[:bottom_n]:
        diagnosis, fix = diagnostic_tree[worst_metric]
        failures.append({
            "question": r.question,
            "answer": r.answer,
            "ground_truth": r.ground_truth,
            "avg_score": avg,
            "worst_metric": worst_metric,
            "score": worst_score,
            "diagnosis": diagnosis,
            "suggested_fix": fix,
        })
    return failures


def save_report(results: dict, failures: list[dict], path: str = "ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
