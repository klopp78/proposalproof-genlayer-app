# Aave proposal 359 verification fixture

This document supplies public inputs for the ProposalProof v2 demo. It does not replace the canonical governance or block-explorer records. The contract persists the exact rendered excerpts and normalized semantic snapshots used during assessment; retrieve them with `get_evidence_pack(assessment_id)`.

## Proposal identity

- Governance: Aave Governance
- Proposal ID: 359
- Proposal hash: `0x5c6bcd27cc94e27f40112647e0fde323c17706ce82746008ceae9d707deb0208`
- Canonical proposal: https://vote.onaave.com/proposal/?ipfsHash=0x5c6bcd27cc94e27f40112647e0fde323c17706ce82746008ceae9d707deb0208&proposalId=359

## Approved action

Call `claimRewardsOnBehalf()` for Sablier Legacy v1.1 and distribute `895805689180182547296` wei of AAVE to `sablier.eth`.

## Execution record

- Target chain: Ethereum
- Chain ID: `1`
- Transaction: `0x7a41b0b367d7914389edfdf132c9031fb6379bb97e7b6b0139c02ffd087f1ded`
- Canonical transaction: https://etherscan.io/tx/0x7a41b0b367d7914389edfdf132c9031fb6379bb97e7b6b0139c02ffd087f1ded
- Governance discussion: https://governance.aave.com/t/arfc-claiming-aave-rewards-for-the-sablier-legacy-v1-1-contract/21975

## Integrity note

ProposalProof passes the complete source bundle plus the normalized `1:0x7a41...f1ded` execution identity to the deployed GenLayer contract. Validators compare decision-critical semantic snapshots rather than volatile page chrome. The accepted record binds destination addresses, decoded calls, values, parameters, block number, execution time, provider-family independence, and a retrievable exact evidence pack. The application displays finalized contract state and never calculates a local verdict.
