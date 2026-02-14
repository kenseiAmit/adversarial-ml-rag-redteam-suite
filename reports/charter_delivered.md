# Red Team Charter

## Engagement Details

| Field | Value |
|---|---|
| **Engagement Name** | Project FinanceGuard AI Red Team Assessment |
| **Date** | October 18, 2026 |
| **Assessor** | Junior AI Red Team Operator (FinanceGuard Security Operations) |
| **Sponsor** | Head of AI Security & Chief Information Security Officer (CISO) |

## Objectives

This red team engagement evaluates the adversarial robustness, data confidentiality, policy integrity, and deployment supply chain posture of FinanceGuard Inc.'s core AI production systems. Specifically, testing focuses on five distinct attack vectors:

1. **Adversarial Evasion (FGSM):** Evaluate the vulnerability of the `ReceiptCNN` visual expense classifier against gradient-based adversarial perturbations (Fast Gradient Sign Method) designed to deceive automated receipt verification without visual human detection.
2. **Data Poisoning (Label Flipping):** Determine the vulnerability of `ReceiptCNN` to stealthy dataset poisoning by introducing label flips during training ($\le 10\%$ corrupted labels) to induce systematic model degradation on clean inputs.
3. **Prompt Injection:** Assess the FinanceGuard Expense Policy RAG Chatbot against direct prompt injection, role hijacking, instruction override, policy contradiction, and encoded payloads to test system prompt containment and behavioural guardrails.
4. **Data Exfiltration:** Exploit vector search retrieval mechanisms within the FAISS-backed RAG chatbot to exfiltrate restricted corporate documents (specifically executive compensation and bonus structures) lacking document-level access control.
5. **Supply Chain & Deployment Analysis:** Perform container image vulnerability scanning and Docker configuration analysis to discover exploitable dependencies, container escape vectors, and insecure build practices.

## Scope

### In Scope
- **ReceiptCNN Classifier:** PyTorch deep convolutional neural network for automated receipt detection, including clean baseline model (`checkpoints/receipt_cnn_clean.pt`), training pipeline (`train.py`), evaluation suite (`evaluate.py`), and test image dataset (`balanced_data/`).
- **FinanceGuard Expense RAG Chatbot:** Flask REST API (`app.py`, `rag.py`, `build_index.py`), FAISS vector index (`faiss_index/`), document ingestion pipeline, and corporate knowledge base documents (`data/policies/`).
- **Container Deployment Pipeline:** Production Dockerfile (`Dockerfile`) and software bill of materials / container vulnerability report (`06_trivy_report.json`).

### Out of Scope
- Production hosting infrastructure outside designated local test environments (e.g., cloud VPC networks, corporate IAM providers).
- Denial of Service (DoS/DDoS) attacks against third-party API providers (OpenAI API endpoints).
- Physical security, social engineering of real company employees, or non-AI internal enterprise networks.

## Rules of Engagement

1. **Safety & Containment:** All adversarial testing must be performed within controlled test sandboxes; all synthetic attacks, poisoned checkpoints, and exfiltration scripts must remain quarantined in local workspace directories.
2. **Ethical Handling of Sensitive Data:** Any sensitive or confidential executive compensation data retrieved during exfiltration testing must only be documented in designated red team vulnerability logs and not exported to external destinations.
3. **Reproducibility & Verification:** Every attack vector must be backed by concrete code, logged raw metrics, and reproducible execution scripts with zero synthetic mocking or simulated outputs.
4. **Attribution & Least Privilege:** All API calls and model evaluations must run with explicit security logging and resource attribution flags enabled.

## Success Criteria

| Attack Vector | Success Metric |
|---|---|
| **FGSM Evasion** | Measure degradation across $\epsilon \in [0.0, 0.15]$; achieve significant adversarial accuracy degradation ($<50\%$ accuracy) with perturbation imperceptible to casual review ($\epsilon \le 0.05$). |
| **Label-Flip Poisoning** | Execute training set label flip at $\le 10\%$ corruption; verify poisoned model accuracy on clean test set drops by at least 5 percentage points relative to clean baseline ($94.36\%$). |
| **Prompt Injection** | Execute 5 distinct attack strategies against RAG chatbot; successfully bypass intended persona/guardrails or induce confidential retrieval disclosure in at least one vector. |
| **Data Exfiltration** | Formulate 6 varied semantic queries targeting executive compensation; retrieve restricted document (`executive_bonus_structure_CONFIDENTIAL.md`) and extract private salary/multiplier/stock metrics in $\ge 3$ queries. |
| **Supply Chain Analysis** | Identify all High/Critical CVEs across container base OS and Python packages; audit Dockerfile against 6 container hardening benchmarks with concrete remediation steps. |

## Deliverables

1. **Red Team Charter (`charter_delivered.md`):** Complete authorization, scoping, rules of engagement, and measurable success criteria.
2. **Vulnerability Log (`vulnerability_log_delivered.md`):** Consolidated register of discovered vulnerabilities (VUL-001 through VUL-005) with CVSS/severity ratings, evidence, and remediation roadmaps.
3. **FGSM Evasion Results (`fgsm_results_delivered.md`):** Comprehensive evaluation table across 6 epsilon values, baseline metrics, side-by-side visual perturbation evidence, and financial impact analysis.
4. **Data Poisoning Results (`poisoning_results_delivered.md`):** Poisoning configuration details, visual evidence of flipped training pairs, clean vs. poisoned comparative metrics table, confusion matrices, and threat model analysis.
5. **Prompt Injection Transcript (`prompt_injection_transcript_delivered.md`):** Detailed attack transcripts for all 5 injection strategies, indicator matching results, retrieval leakage analysis, and defensive recommendations.
6. **Data Exfiltration Evidence (`data_exfiltration_evidence_delivered.md`):** Complete evaluation of 6 exfiltration queries, leaked executive compensation metrics, architectural root cause analysis of FAISS vector stores, and multi-tier mitigations.
7. **Supply Chain Analysis (`supply_chain_analysis_delivered.md`):** Trivy vulnerability audit breakdown, critical CVE analysis, 6 Dockerfile architectural issues with hardened configurations, and AI pipeline risk assessment.
8. **Executive Summary (`executive_summary_delivered.md`):** High-level risk dashboard, business-impact analysis for executive leadership, prioritized remediation matrix, and strategic roadmaps.
9. **Reproduction Steps (`reproduction_steps_delivered.md`):** Fully validated, copy-pasteable command line instructions for end-to-end verification and reproduction of all findings.
