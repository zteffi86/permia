# Gate-0 Validation Protocol

## Objective
Validate AI extraction + deterministic evaluation on 20 past approved restaurant applications before pilot deployment.

## Success Criteria
- **Auto-decision rate:** ≥70% (14+ of 20 applications)
- **False negative rate:** ≤5% (≤1 of 20)
- **Inspector disagreement:** ≤10% (18+ of 20 agree with deterministic failures)

## Test Dataset
- **N = 20** past approved applications from Reykjavík Health Department
- **Stratification:**
  - 10 full-service restaurants
  - 5 cafés/coffee shops
  - 5 quick-service/take-away
- **Time window:** Last 18 months (Jan 2024 - Jun 2025)
- **Redaction:** Remove PII; retain timestamps, geodata, evidence

## Process
1. **Blind processing:** Run all 20 through Permía end-to-end
2. **Compare outcomes:** Permía vs. historical approval decisions
3. **Inspector review:** For discrepancies, inspector determines false positive/negative

## Deliverables
- Confusion matrices per rule category
- Per-assertion precision/recall/F1 scores
- 5 specimen evaluation reports
- Evidence hash manifest
- Published validation report (public)

## Action on Failure
- Move underperforming assertions to attestation-first
- Defer complex rules to Phase 2
- Raise evidence quality standards
