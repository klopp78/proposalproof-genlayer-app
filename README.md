# ProposalProof for GenLayer

ProposalProof is an interactive governance execution verification console backed by the ProposalExecutionGuard v2 Intelligent Contract. It binds an approved proposal to one normalized blockchain execution identity and stores a durable consensus receipt plus the exact evidence pack used during assessment.

## Canonical source

- The sole v2 contract source is [`contracts/proposal_execution_guard.py`](contracts/proposal_execution_guard.py).
- The deployed source is pinned to commit [`9a9854c8ddb59a2a9d04207b980bc21c3b2f1ec5`](https://github.com/klopp78/proposalproof-genlayer-app/blob/9a9854c8ddb59a2a9d04207b980bc21c3b2f1ec5/contracts/proposal_execution_guard.py).
- Its SHA-256 digest is `e308037aceeb8cc556d824907e42d5202dee62150338e9e0916b24f321ce25ed`.
- The frontend ABI calls the same v2 methods, including `get_evidence_pack` and `get_execution_claim(chain_id, transaction_hash)`.
- The machine-readable deployment mapping is in [`evidence/deployment-manifest.json`](evidence/deployment-manifest.json).

## Verification model

- Execution identity is `chain_id:transaction_hash`, never a URL string.
- The execution URL must bind that hash on a supported authoritative explorer.
- Source independence uses provider families, so aliases and subdomains from Etherscan, GitHub, Aave, or Blockscout are not counted as separate evidence providers.
- Validators extract and compare decision-critical facts: proposal status, transaction status, destinations, decoded calls, values, parameters, block number, execution time, proposal identity, and action match.
- Consensus compares canonical semantic snapshots, so irrelevant navigation, prices, ads, and other page churn do not alter the decision commitment.
- Exact rendered excerpts, raw hashes, normalized facts, and semantic hashes are stored in a retrievable evidence pack.
- Successful writes require finalized GenVM execution and exact `LATEST_FINAL` state readback in the app.

## Persistent API

```python
assess_execution(governance_name, proposal_id, proposal_url, execution_chain_id,
                 execution_tx_hash, execution_tx_url, declared_actions, source_urls) -> str
get_assessment(assessment_id) -> str
get_evidence_pack(assessment_id) -> str
get_execution_claim(chain_id, transaction_hash) -> str
get_latest_assessment_id() -> str
get_assessment_count() -> u64
list_assessment_ids() -> str
```

## Authoritative deployment

- StudioNet contract: `0x4954181E604f7EA275Ce4BD4F4E3565792231105`
- Contract explorer: https://explorer-studio.genlayer.com/address/0x4954181E604f7EA275Ce4BD4F4E3565792231105
- Finalized assessment transaction: https://explorer-studio.genlayer.com/tx/0x58fe5158fd5784148bf87f8e811300dd17e85b0a4b4f9192f3b4213128d60016
- Receipt: `peg_51f28f589fe67ae7a480`
- Deployed source commit: `9a9854c8ddb59a2a9d04207b980bc21c3b2f1ec5`

This is the only deployment used by the v2 frontend. Earlier addresses are legacy v1 deployments.

## Live application

- App: https://klopp78.github.io/proposalproof-genlayer-app/
- Evidence example: [evidence/aave-359.md](evidence/aave-359.md)

## Tests

```bash
npm test
```

The test suite runs contract marker checks, mocked GenVM leader/validator behavior, adversarial identity and provider-family tests, the Next/Vinext production build, and the static GitHub Pages build.

`test:behavior` discovers an available `python3`, `python`, or Windows `py -3` interpreter, so it does not depend on a contributor-specific filesystem path. The cases explicitly cover explorer aliases for one execution identity, altered transaction parameters, provider-family aliases, irrelevant dynamic page changes, validator disagreement, and complete GenVM write/readback behavior.
