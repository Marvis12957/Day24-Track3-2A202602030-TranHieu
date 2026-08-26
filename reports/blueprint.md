# CI/CD Blueprint: RAG Eval + Guardrail Stack

**Sinh viên:** Trần Hiếu - 2A202602030  
**Ngày:** 2026-08-27

---

## Guard Stack Architecture

```
User Input
    │
    ▼ (~?ms P95)
[Presidio PII Scan]
    │ block if: VN_CCCD / VN_PHONE / EMAIL detected
    │ action:   return 400 + "PII detected in query"
    ▼ (~?ms P95)
[NeMo Input Rail]
    │ block if: off-topic / jailbreak / prompt injection
    │ action:   return 503 + refuse message
    ▼
[RAG Pipeline (Day 18)]
    │ M1 Chunk → M2 Search → M3 Rerank → GPT-4o-mini
    ▼
[NeMo Output Rail]
    │ flag if:  PII in response / sensitive content
    │ action:   replace with safe response
    ▼
User Response
```

---

## Latency Budget

*(Điền từ kết quả Task 12 — measure_p95_latency())*

| Layer | P50 (ms) | P95 (ms) | P99 (ms) | Budget |
|---|---|---|---|---|
| Presidio PII | ? | ? | ? | <10ms |
| NeMo Input Rail | ? | ? | ? | <300ms |
| RAG Pipeline | ? | ? | ? | <2000ms |
| NeMo Output Rail | ? | ? | ? | <300ms |
| **Total Guard** | ? | **?** | ? | **<500ms** |

**Budget OK?** [ ] Yes / [ ] No  
**Comment:** [Nếu vượt budget, layer nào là bottleneck và cách tối ưu?]

---

## CI/CD Gates (phải pass trước khi merge to main)

```yaml
# .github/workflows/rag_eval.yml
- name: RAGAS Quality Gate
  run: python src/phase_a_ragas.py
  env:
    MIN_FAITHFULNESS: 0.75
    MIN_AVG_SCORE: 0.65

- name: Guardrail Gate
  run: pytest tests/test_phase_c.py -k "test_adversarial_suite_pass_rate"
  # phải ≥ 15/20 (75%)

- name: Latency Gate
  run: python -c "from src.phase_c_guard import measure_p95_latency; ..."
  # P95 total < 500ms
```

---

## Monitoring Dashboard (production)

| Metric | Alert Threshold | Action |
|---|---|---|
| RAGAS faithfulness (daily sample) | < 0.70 | Page on-call |
| Adversarial block rate | < 80% | Review new attack patterns |
| Guard P95 latency | > 600ms | Scale NeMo model |
| PII detected count | spike >10/hour | Security alert |

---

## Kết quả thực tế từ Lab

| | Kết quả |
|---|---|
| RAGAS avg_score (50q) | ? |
| Worst metric | ? |
| Dominant failure distribution | ? |
| Cohen's κ | ? |
| Adversarial pass rate | ? / 20 |
| Guard P95 latency | ? ms |

---

## Nhận xét & Cải tiến

> [Viết 3-5 câu về: điều gì hoạt động tốt, điều gì cần cải thiện,
>  nếu deploy production thực sự bạn sẽ thay đổi gì trong stack này?]
