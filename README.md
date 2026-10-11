# ProposalProof for GenLayer

ProposalProof is an interactive governance execution verification console backed by the ProposalExecutionGuard v2 Intelligent Contract. It binds an approved proposal to one normalized blockchain execution identity and stores a durable consensus receipt plus the exact evidence pack used during assessment.

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

The v2 StudioNet address and a finalized verification receipt will be recorded here immediately after deployment. Earlier addresses are legacy v1 deployments and are not used by the v2 frontend.

## Live application

- App: https://klopp78.github.io/proposalproof-genlayer-app/
- Evidence example: [evidence/aave-359.md](evidence/aave-359.md)

## Tests

```bash
npm test
```

The test suite runs contract marker checks, mocked GenVM leader/validator behavior, adversarial identity and provider-family tests, the Next/Vinext production build, and the static GitHub Pages build.
