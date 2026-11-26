# PHOENIX-R — Collective Correctability in Co-Evolving Human–AI Information Ecosystems

Research prototype | November 2026 | Mohammad Amanlou

**Question:** Can AI-mediated coordination reduce collective capacity to discover, verify, transmit and adopt corrections even when initial claim accuracy, query budgets and individual access marginals are controlled? Can we audit hidden collective failure without confusing a prospective intervention with an after-the-fact readout?

**Status:** Exploratory research, not a conference submission or claim of established priority. All reported experimental results are synthetic or deterministic scripted text runs. No human-participant or actual LLM trial has been completed. Current implementation is a closed-world simulator and exact small-instance analyses, not a deployed system or finished hypergraph/RL model.

## Repository map

| Directory | Contents |
| --- | --- |
| [research/v1](research/v1) | Joint repair non-identifiability, LP and synthetic audit experiments. |
| [research/v2](research/v2) | Repair-menu audit frontier, exact KL checks and LP results. |
| [research/v3](research/v3) | Endogenous visibility, sequential auditing and robust stress tests. |
| [research/v4](research/v4) | Persistent evidence bank, dynamic simulator, noisy replication stress test, allocation oracle and scripted text pilot. |
| [docs](docs) | Latest adversarial novelty assessment, caveats and publication gates. |
| [scripts](scripts) | Reproduction entry point. |

## Reproduction

Python 3.10+ recommended. From the repository root:

```bash
python -m venv .venv
# activate the environment using your OS's usual command
python -m pip install -r requirements.txt
python scripts/reproduce.py --version all
```

This copies code into `local_runs/` before running, preserving archived output files. Use `--version v1`, `v2`, `v3` or `v4` for a single stage. Read each stage report for parameter assumptions; exact numerical values may vary with dependency versions. The V4 text traces are stored losslessly as `research/v4/text_scripted.jsonl.gz`; Python's `gzip.open` can read them.

## Optional real LLM smoke test (not yet run)

Serve an actual local OpenAI-compatible inference model. After installing requirements, run:

```bash
python research/v4/text_env.py --backend llm --model YOUR_SERVED_MODEL --endpoint http://localhost:8000/v1/chat/completions --cases 4
```

Optional authentication is supplied through the local environment, never committed. The initial text pilot uses fictional claims and an oracle gate; do not treat it as human evidence or a realistic fact-checking benchmark. Equal query count does not guarantee equal token or time cost.

## Evidence and novelty

Read [the current novelty assessment](docs/NOVELTY_ASSESSMENT.md) before citing this project. The mathematical tools and many component ideas have strong precedents; the candidate research contribution is a specific controlled causal question about joint repair failure, prospective evidence creation versus retrospective observability, and a cost-matched intervention. Negative outcomes and limitations are part of the research record. No license has been assigned pending the author's decision.
