# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Consensus receipts binding governance proposals to normalized execution facts."""

from genlayer import *
import hashlib
import json
import typing


class ProposalExecutionGuard(gl.Contract):
    """Append-only governance execution assessments with retrievable evidence packs."""

    assessment_count: u64
    latest_assessment_id: str
    assessment_ids: DynArray[str]
    assessments: TreeMap[str, str]
    evidence_packs: TreeMap[str, str]
    claimed_executions: TreeMap[str, str]

    def __init__(self):
        self.assessment_count = u64(0)
        self.latest_assessment_id = ""

    @gl.public.view
    def get_assessment_count(self) -> u64:
        return self.assessment_count

    @gl.public.view
    def get_latest_assessment_id(self) -> str:
        return self.latest_assessment_id

    @gl.public.view
    def get_assessment(self, assessment_id: str) -> str:
        return self.assessments.get(assessment_id, "")

    @gl.public.view
    def get_evidence_pack(self, assessment_id: str) -> str:
        return self.evidence_packs.get(assessment_id, "")

    @gl.public.view
    def list_assessment_ids(self) -> str:
        return json.dumps([item for item in self.assessment_ids], separators=(",", ":"))

    @gl.public.view
    def get_execution_claim(self, chain_id: str, transaction_hash: str) -> str:
        execution_id = _execution_id(_chain_id(chain_id), _transaction_hash(transaction_hash))
        return self.claimed_executions.get(execution_id, "")

    @gl.public.write
    def assess_execution(
        self,
        governance_name: str,
        proposal_id: str,
        proposal_url: str,
        execution_chain_id: str,
        execution_tx_hash: str,
        execution_tx_url: str,
        declared_actions: str,
        source_urls: DynArray[str],
    ) -> str:
        governance = _short_text(governance_name, "governance_name", 2, 160)
        proposal = _short_text(proposal_id, "proposal_id", 1, 120)
        canonical_proposal_url = _https_url(proposal_url)
        chain_id = _chain_id(execution_chain_id)
        tx_hash = _transaction_hash(execution_tx_hash)
        canonical_execution_url = _execution_url(execution_tx_url, chain_id, tx_hash)
        actions = _long_text(declared_actions, "declared_actions", 10, 6000)
        urls = _validate_sources([item for item in source_urls])
        if canonical_proposal_url not in urls or canonical_execution_url not in urls:
            raise Exception("proposal_and_execution_urls_must_be_sources")

        manifest = _source_manifest(urls, canonical_proposal_url, canonical_execution_url)
        if len({item["independence_key"] for item in manifest}) < 2:
            raise Exception("at_least_two_independent_source_families_required")
        execution_sources = [item for item in manifest if item["role"] == "execution"]
        if len(execution_sources) != 1 or not execution_sources[0]["authoritative"]:
            raise Exception("authoritative_execution_explorer_required")

        execution_id = _execution_id(chain_id, tx_hash)
        action_hash = _sha256(actions)
        context_hash = _sha256_parts([
            "proposalexecutionguard.v2", governance, proposal, canonical_proposal_url,
            chain_id, tx_hash, action_hash, _canonical_json(manifest),
        ])

        def leader_fn():
            return _evaluate_execution(
                governance, proposal, canonical_proposal_url, chain_id, tx_hash,
                canonical_execution_url, actions, urls, manifest, context_hash,
            )

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                proposed = _parse_result(leader_result.calldata, require_evidence=True)
                independent = _parse_result(leader_fn(), require_evidence=True)
            except Exception:
                return False
            return _consensus_view(proposed) == _consensus_view(independent)

        result = _parse_result(gl.vm.run_nondet_unsafe(leader_fn, validator_fn), require_evidence=True)
        if result["decision"] == "executed_match":
            existing = self.claimed_executions.get(execution_id, "")
            if existing != "":
                raise Exception("execution_already_claimed")

        self.assessment_count = u64(int(self.assessment_count) + 1)
        sequence = int(self.assessment_count)
        assessment_id = "peg_" + _sha256_parts([context_hash, execution_id, str(sequence)])[:20]
        evidence_pack = {
            "schema_version": "proposalexecutionguard.evidence.v2",
            "assessment_id": assessment_id,
            "assessment_context_hash": context_hash,
            "semantic_snapshot_bundle_hash": result["semantic_snapshot_bundle_hash"],
            "raw_snapshot_bundle_hash": result["raw_snapshot_bundle_hash"],
            "snapshots": result["evidence_snapshots"],
        }
        evidence_pack_hash = _sha256(_canonical_json(evidence_pack))
        record = {
            "schema_version": "proposalexecutionguard.v2",
            "assessment_id": assessment_id,
            "sequence": sequence,
            "governance_name": governance,
            "proposal_id": proposal,
            "proposal_url": canonical_proposal_url,
            "execution_chain_id": chain_id,
            "execution_tx_hash": tx_hash,
            "execution_tx_url": canonical_execution_url,
            "execution_id": execution_id,
            "declared_actions": actions,
            "declared_actions_hash": action_hash,
            "assessment_context_hash": context_hash,
            "source_manifest": manifest,
            "semantic_snapshot_hashes": result["semantic_snapshot_hashes"],
            "semantic_snapshot_bundle_hash": result["semantic_snapshot_bundle_hash"],
            "raw_snapshot_bundle_hash": result["raw_snapshot_bundle_hash"],
            "evidence_pack_hash": evidence_pack_hash,
            "submitted_by": str(gl.message.sender_address).lower(),
            "decision": result["decision"],
            "proposal_status": result["proposal_status"],
            "execution_status": result["execution_status"],
            "confidence": result["confidence"],
            "proposal_match": result["proposal_match"],
            "action_match": result["action_match"],
            "execution_tx_match": result["execution_tx_match"],
            "executed_at_utc": result["executed_at_utc"],
            "destination_addresses": result["destination_addresses"],
            "function_calls": result["function_calls"],
            "values_wei": result["values_wei"],
            "parameters_hash": result["parameters_hash"],
            "block_number": result["block_number"],
            "supporting_source_count": result["supporting_source_count"],
            "independent_source_count": result["independent_source_count"],
            "readable_source_count": result["readable_source_count"],
        }
        record_hash = _sha256(_canonical_json(record))
        record["accepted_write"] = {
            "assessment_id": assessment_id,
            "record_hash": record_hash,
            "evidence_pack_hash": evidence_pack_hash,
            "semantic_snapshot_bundle_hash": result["semantic_snapshot_bundle_hash"],
            "execution_id": execution_id,
        }
        self.assessments[assessment_id] = _canonical_json(record)
        self.evidence_packs[assessment_id] = _canonical_json(evidence_pack)
        self.assessment_ids.append(assessment_id)
        self.latest_assessment_id = assessment_id
        if result["decision"] == "executed_match":
            self.claimed_executions[execution_id] = assessment_id
        return assessment_id


def _evaluate_execution(
    governance: str,
    proposal: str,
    proposal_url: str,
    chain_id: str,
    tx_hash: str,
    execution_url: str,
    actions: str,
    urls: typing.Sequence[str],
    manifest: typing.Sequence[dict],
    context_hash: str,
) -> str:
    semantic_snapshots = []
    evidence_snapshots = []
    readable_count = 0
    for index, url in enumerate(urls):
        try:
            rendered = gl.nondet.web.render(url, mode="text")[:7000]
            readable = len(rendered.strip()) >= 40
        except Exception:
            rendered = "SOURCE_UNAVAILABLE"
            readable = False
        if readable:
            readable_count += 1
            observed = _extract_source_facts(
                rendered, manifest[index], governance, proposal, chain_id, tx_hash, actions,
            )
            if manifest[index]["role"] == "execution" and manifest[index]["authoritative"]:
                # The canonical explorer URL itself authoritatively binds network and tx identity.
                if observed["chain_id"] == "":
                    observed["chain_id"] = _explorer_chain_id(_host(url))
                if observed["tx_hash"] == "":
                    observed["tx_hash"] = tx_hash
        else:
            observed = _empty_observation()
        semantic = {
            "source_index": index + 1,
            "role": manifest[index]["role"],
            "independence_key": manifest[index]["independence_key"],
            "authoritative": manifest[index]["authoritative"],
            "readable": readable,
            "observed": observed,
        }
        raw_hash = _sha256(rendered)
        semantic_hash = _sha256(_canonical_json(semantic))
        semantic_snapshots.append(semantic)
        evidence_snapshots.append({
            "source_index": index + 1,
            "url": url,
            "raw_excerpt": rendered,
            "raw_excerpt_hash": raw_hash,
            "semantic_snapshot": semantic,
            "semantic_snapshot_hash": semantic_hash,
        })

    semantic_hashes = [_sha256(_canonical_json(item)) for item in semantic_snapshots]
    raw_hashes = [item["raw_excerpt_hash"] for item in evidence_snapshots]
    semantic_bundle_hash = _sha256_parts([context_hash, _canonical_json(semantic_hashes)])
    raw_bundle_hash = _sha256_parts([context_hash, _canonical_json(raw_hashes)])
    result = _adjudicate(
        governance, proposal, proposal_url, chain_id, tx_hash, execution_url,
        actions, semantic_snapshots, manifest, context_hash,
    )
    proposal_snapshots = [item for item in semantic_snapshots if item["role"] == "proposal" and item["readable"]]
    execution_snapshots = [item for item in semantic_snapshots if item["role"] == "execution" and item["authoritative"] and item["readable"]]
    proposal_observed = proposal_snapshots[0]["observed"] if len(proposal_snapshots) == 1 else _empty_observation()
    execution_observed = execution_snapshots[0]["observed"] if len(execution_snapshots) == 1 else _empty_observation()
    proposal_identity_verified = proposal_observed["proposal_id"] == proposal
    execution_identity_verified = (
        execution_observed["chain_id"] == chain_id and execution_observed["tx_hash"] == tx_hash
    )
    result["proposal_status"] = proposal_observed["proposal_status"]
    result["proposal_match"] = bool(result["proposal_match"] and proposal_identity_verified)
    result["execution_status"] = execution_observed["execution_status"]
    result["execution_tx_match"] = bool(result["execution_tx_match"] and execution_identity_verified)
    result["executed_at_utc"] = execution_observed["executed_at_utc"]
    result["destination_addresses"] = execution_observed["destination_addresses"]
    result["function_calls"] = execution_observed["function_calls"]
    result["values_wei"] = execution_observed["values_wei"]
    result["parameters_canonical"] = execution_observed["parameters_canonical"]
    result["parameters_hash"] = _sha256(execution_observed["parameters_canonical"])
    result["block_number"] = execution_observed["block_number"]
    if not proposal_identity_verified or not execution_identity_verified:
        result.update({
            "decision": "disputed", "confidence": 100, "action_match": False,
            "supporting_source_count": 0,
        })
    result.update({
        "readable_source_count": readable_count,
        "independent_source_count": len({
            item["independence_key"] for item in semantic_snapshots if item["readable"]
        }),
        "semantic_snapshot_hashes": semantic_hashes,
        "semantic_snapshot_bundle_hash": semantic_bundle_hash,
        "raw_snapshot_bundle_hash": raw_bundle_hash,
        "assessment_context_hash": context_hash,
        "evidence_snapshots": evidence_snapshots,
    })
    return _canonical_json(result)


def _extract_source_facts(
    rendered: str,
    manifest_item: dict,
    governance: str,
    proposal: str,
    chain_id: str,
    tx_hash: str,
    actions: str,
) -> dict:
    prompt = f"""
Extract only decision-critical governance and blockchain facts from this public source. Ignore
navigation, prices, ads, timestamps unrelated to execution, and other page noise. Never infer a
transaction field that is not explicitly shown. The expected governance is {governance}, proposal
ID is {proposal}, execution chain ID is {chain_id}, and transaction hash is {tx_hash}. The approved
actions claim is: {actions}

Source role: {manifest_item['role']}
Authoritative execution explorer: {manifest_item['authoritative']}
Rendered source: {rendered}

Return minified JSON with exactly: proposal_id (string), proposal_status
(passed|rejected|cancelled|active|unknown), chain_id (decimal string or empty), tx_hash (0x hash or
empty), execution_status (success|failed|not_found|unknown), destination_addresses (sorted array of
lowercase 0x addresses), function_calls (sorted array of normalized signatures or selectors),
values_wei (sorted array of decimal strings), parameters_canonical (string, empty if unavailable),
block_number (decimal string or empty), executed_at_utc (ISO-8601 UTC or empty),
supports_declared_actions (boolean), supports_proposal_execution_link (boolean). No prose.
"""
    raw = json.loads(gl.nondet.exec_prompt(prompt))
    return _parse_observation(raw)


def _adjudicate(
    governance: str,
    proposal: str,
    proposal_url: str,
    chain_id: str,
    tx_hash: str,
    execution_url: str,
    actions: str,
    semantic_snapshots: typing.Sequence[dict],
    manifest: typing.Sequence[dict],
    context_hash: str,
) -> dict:
    prompt = f"""
Adjudicate whether a governance proposal was executed exactly as approved using only the normalized
decision-critical facts below. Do not use URL text as transaction identity. The canonical execution
identity is chain ID {chain_id} plus transaction hash {tx_hash}. A successful match requires an
authoritative execution snapshot with that exact identity, success status, destination addresses,
function calls, values and parameters; a passed proposal; and support from at least two independent
source families. Use disputed for conflicting critical facts and mismatch for a confirmed execution
whose calls differ from the approved actions.

Governance: {governance}
Proposal ID: {proposal}
Proposal URL: {proposal_url}
Execution URL: {execution_url}
Approved actions: {actions}
Manifest: {_canonical_json(manifest)}
Normalized snapshots: {_canonical_json(semantic_snapshots)}
Context commitment: {context_hash}

Return minified JSON with exactly: decision
(executed_match|passed_not_executed|mismatch|rejected_or_cancelled|disputed|insufficient_evidence),
proposal_status (passed|rejected|cancelled|active|unknown), execution_status
(success|failed|not_found|unknown), confidence (0-100), proposal_match (boolean), action_match
(boolean), execution_tx_match (boolean), executed_at_utc (ISO-8601 UTC or empty),
destination_addresses (sorted lowercase array), function_calls (sorted array), values_wei (sorted
decimal-string array), parameters_canonical (string), block_number (decimal string or empty), and
supporting_source_count (integer). No prose.
"""
    return _parse_decision(json.loads(gl.nondet.exec_prompt(prompt)), chain_id, tx_hash)


def _parse_observation(raw: dict) -> dict:
    proposal_status = _enum(raw.get("proposal_status"), ("passed", "rejected", "cancelled", "active", "unknown"), "unknown")
    execution_status = _enum(raw.get("execution_status"), ("success", "failed", "not_found", "unknown"), "unknown")
    observed_hash = str(raw.get("tx_hash", "")).strip().lower()
    if observed_hash != "":
        observed_hash = _transaction_hash(observed_hash)
    observed_chain = str(raw.get("chain_id", "")).strip()
    if observed_chain != "":
        observed_chain = _chain_id(observed_chain)
    return {
        "proposal_id": _bounded(str(raw.get("proposal_id", "")).strip(), 120),
        "proposal_status": proposal_status,
        "chain_id": observed_chain,
        "tx_hash": observed_hash,
        "execution_status": execution_status,
        "destination_addresses": _addresses(raw.get("destination_addresses", [])),
        "function_calls": _strings(raw.get("function_calls", []), 16, 180),
        "values_wei": _decimal_strings(raw.get("values_wei", []), 16),
        "parameters_canonical": _bounded(str(raw.get("parameters_canonical", "")).strip(), 2500),
        "block_number": _optional_decimal(raw.get("block_number", "")),
        "executed_at_utc": _optional_timestamp(raw.get("executed_at_utc", "")),
        "supports_declared_actions": bool(raw.get("supports_declared_actions", False)),
        "supports_proposal_execution_link": bool(raw.get("supports_proposal_execution_link", False)),
    }


def _parse_decision(raw: dict, chain_id: str, tx_hash: str) -> dict:
    decision = _enum(raw.get("decision"), (
        "executed_match", "passed_not_executed", "mismatch", "rejected_or_cancelled",
        "disputed", "insufficient_evidence",
    ), "disputed")
    proposal_status = _enum(raw.get("proposal_status"), ("passed", "rejected", "cancelled", "active", "unknown"), "unknown")
    execution_status = _enum(raw.get("execution_status"), ("success", "failed", "not_found", "unknown"), "unknown")
    confidence = int(raw.get("confidence", -1))
    if confidence < 0 or confidence > 100:
        raise Exception("invalid_confidence")
    destinations = _addresses(raw.get("destination_addresses", []))
    calls = _strings(raw.get("function_calls", []), 32, 180)
    values = _decimal_strings(raw.get("values_wei", []), 32)
    parameters = _bounded(str(raw.get("parameters_canonical", "")).strip(), 4000)
    block_number = _optional_decimal(raw.get("block_number", ""))
    executed_at = _optional_timestamp(raw.get("executed_at_utc", ""))
    supporting_count = int(raw.get("supporting_source_count", -1))
    flags = ("proposal_match", "action_match", "execution_tx_match")
    if supporting_count < 0 or supporting_count > 5 or any(not isinstance(raw.get(item), bool) for item in flags):
        raise Exception("invalid_decision_fields")
    if decision == "executed_match" and (
        proposal_status != "passed" or execution_status != "success"
        or not raw["proposal_match"] or not raw["action_match"] or not raw["execution_tx_match"]
        or supporting_count < 2 or executed_at == "" or block_number == ""
        or len(destinations) == 0 or len(calls) == 0
    ):
        raise Exception("executed_match_requires_authoritative_complete_proof")
    return {
        "decision": decision,
        "proposal_status": proposal_status,
        "execution_status": execution_status,
        "confidence": confidence,
        "proposal_match": raw["proposal_match"],
        "action_match": raw["action_match"],
        "execution_tx_match": raw["execution_tx_match"],
        "executed_at_utc": executed_at,
        "destination_addresses": destinations,
        "function_calls": calls,
        "values_wei": values,
        "parameters_canonical": parameters,
        "parameters_hash": _sha256(parameters),
        "block_number": block_number,
        "supporting_source_count": supporting_count,
        "normalized_execution_identity": _execution_id(chain_id, tx_hash),
    }


def _parse_result(raw: str, require_evidence: bool) -> dict:
    result = json.loads(raw)
    identity = str(result.get("normalized_execution_identity", ""))
    if ":" not in identity:
        raise Exception("invalid_execution_identity")
    chain_id, tx_hash = identity.split(":", 1)
    parsed = _parse_decision(result, _chain_id(chain_id), _transaction_hash(tx_hash))
    hashes = result.get("semantic_snapshot_hashes", [])
    if not isinstance(hashes, list) or len(hashes) < 2 or len(hashes) > 5 or any(not _is_digest(str(item)) for item in hashes):
        raise Exception("invalid_semantic_snapshot_hashes")
    for field in ("semantic_snapshot_bundle_hash", "raw_snapshot_bundle_hash", "assessment_context_hash"):
        if not _is_digest(str(result.get(field, ""))):
            raise Exception("invalid_commitment")
    snapshots = result.get("evidence_snapshots", [])
    if require_evidence:
        if not isinstance(snapshots, list) or len(snapshots) != len(hashes):
            raise Exception("invalid_evidence_pack")
        for index, snapshot in enumerate(snapshots):
            if _sha256(str(snapshot.get("raw_excerpt", ""))) != str(snapshot.get("raw_excerpt_hash", "")):
                raise Exception("raw_snapshot_hash_mismatch")
            if _sha256(_canonical_json(snapshot.get("semantic_snapshot", {}))) != hashes[index]:
                raise Exception("semantic_snapshot_hash_mismatch")
    parsed.update({
        "readable_source_count": int(result.get("readable_source_count", -1)),
        "independent_source_count": int(result.get("independent_source_count", -1)),
        "semantic_snapshot_hashes": [str(item) for item in hashes],
        "semantic_snapshot_bundle_hash": str(result["semantic_snapshot_bundle_hash"]),
        "raw_snapshot_bundle_hash": str(result["raw_snapshot_bundle_hash"]),
        "assessment_context_hash": str(result["assessment_context_hash"]),
        "evidence_snapshots": snapshots,
    })
    if parsed["readable_source_count"] < 0 or parsed["readable_source_count"] > len(hashes):
        raise Exception("invalid_readable_source_count")
    if parsed["independent_source_count"] < 0 or parsed["independent_source_count"] > len(hashes):
        raise Exception("invalid_independent_source_count")
    return parsed


def _consensus_view(result: dict) -> str:
    # A positive execution match is strict: every consequential fact must agree. Different
    # conservative outcomes are equivalent safe failures and must not split consensus merely
    # because public pages expose incomplete or differently formatted details to validators.
    fields = ["assessment_context_hash", "normalized_execution_identity"]
    positive = result["decision"] == "executed_match"
    view = {field: result[field] for field in fields}
    view["positive_execution_match"] = positive
    if positive:
        strict_fields = (
            "proposal_status", "execution_status", "proposal_match", "action_match",
            "execution_tx_match", "destination_addresses", "function_calls", "values_wei",
            "parameters_hash", "block_number", "supporting_source_count",
            "independent_source_count",
        )
        view.update({field: result[field] for field in strict_fields})
    return _canonical_json(view)


def _validate_sources(raw_urls: typing.Sequence[str]) -> typing.Sequence[str]:
    if len(raw_urls) < 2 or len(raw_urls) > 5:
        raise Exception("use_two_to_five_sources")
    urls = []
    seen = set()
    for raw in raw_urls:
        url = _https_url(raw)
        key = url.rstrip("/").lower()
        if key in seen:
            raise Exception("duplicate_source_url")
        seen.add(key)
        urls.append(url)
    return urls


def _source_manifest(urls: typing.Sequence[str], proposal_url: str, execution_url: str) -> typing.Sequence[dict]:
    result = []
    for index, url in enumerate(urls):
        host = _host(url)
        role = "proposal" if url == proposal_url else "execution" if url == execution_url else "supporting"
        result.append({
            "source_index": index + 1,
            "url": url,
            "host": host,
            "independence_key": _independence_key(host),
            "role": role,
            "authoritative": role != "execution" or _is_authoritative_execution_host(host),
            "url_hash": _sha256(url),
        })
    return result


def _independence_key(host: str) -> str:
    labels = host.split(".")
    root = ".".join(labels[-2:]) if len(labels) >= 2 else host
    families = {
        "etherscan.io": "etherscan", "basescan.org": "etherscan", "arbiscan.io": "etherscan",
        "optimistic.etherscan.io": "etherscan", "polygonscan.com": "etherscan",
        "bscscan.com": "etherscan", "blockscout.com": "blockscout",
        "github.com": "github", "githubusercontent.com": "github",
        "aave.com": "aave", "onaave.com": "aave",
    }
    for domain, family in families.items():
        if host == domain or host.endswith("." + domain):
            return family
    return root


def _is_authoritative_execution_host(host: str) -> bool:
    domains = (
        "etherscan.io", "basescan.org", "arbiscan.io", "optimistic.etherscan.io",
        "polygonscan.com", "bscscan.com", "blockscout.com",
    )
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def _explorer_chain_id(host: str) -> str:
    chains = {
        "etherscan.io": "1",
        "basescan.org": "8453",
        "arbiscan.io": "42161",
        "optimistic.etherscan.io": "10",
        "polygonscan.com": "137",
        "bscscan.com": "56",
    }
    for domain, chain_id in chains.items():
        if host == domain or host.endswith("." + domain):
            return chain_id
    return ""


def _execution_url(raw: str, chain_id: str, tx_hash: str) -> str:
    url = _https_url(raw)
    host = _host(url)
    if not _is_authoritative_execution_host(host) or tx_hash not in url.lower():
        raise Exception("execution_url_must_bind_authoritative_tx_hash")
    explorer_chain_id = _explorer_chain_id(host)
    if explorer_chain_id != "" and explorer_chain_id != chain_id:
        raise Exception("execution_explorer_chain_mismatch")
    return url


def _execution_id(chain_id: str, tx_hash: str) -> str:
    return chain_id + ":" + tx_hash


def _chain_id(raw: str) -> str:
    value = str(raw).strip()
    if not value.isdigit() or len(value) > 10 or int(value) < 1:
        raise Exception("invalid_chain_id")
    return str(int(value))


def _transaction_hash(raw: str) -> str:
    value = str(raw).strip().lower()
    if len(value) != 66 or not value.startswith("0x") or any(char not in "0123456789abcdef" for char in value[2:]):
        raise Exception("invalid_transaction_hash")
    return value


def _host(url: str) -> str:
    host = url.split("//", 1)[1].split("/", 1)[0].split(":", 1)[0].lower()
    if "." not in host or len(host) > 253:
        raise Exception("invalid_source_host")
    return host


def _https_url(raw: str) -> str:
    value = str(raw).strip()
    if not value.startswith("https://") or len(value) > 600:
        raise Exception("invalid_https_url")
    _host(value)
    return value


def _short_text(raw: str, field: str, minimum: int, maximum: int) -> str:
    value = str(raw).strip()
    if len(value) < minimum or len(value) > maximum or any(char in value for char in "\n\r\t"):
        raise Exception("invalid_" + field)
    return value


def _long_text(raw: str, field: str, minimum: int, maximum: int) -> str:
    value = str(raw).strip()
    if len(value) < minimum or len(value) > maximum or "\x00" in value:
        raise Exception("invalid_" + field)
    return value


def _empty_observation() -> dict:
    return {
        "proposal_id": "", "proposal_status": "unknown", "chain_id": "", "tx_hash": "",
        "execution_status": "unknown", "destination_addresses": [], "function_calls": [],
        "values_wei": [], "parameters_canonical": "", "block_number": "",
        "executed_at_utc": "", "supports_declared_actions": False,
        "supports_proposal_execution_link": False,
    }


def _enum(raw, allowed: typing.Sequence[str], fallback: str) -> str:
    value = str(raw or fallback).strip().lower()
    if value not in allowed:
        raise Exception("invalid_enum_value")
    return value


def _addresses(raw) -> typing.Sequence[str]:
    if not isinstance(raw, list):
        raise Exception("invalid_addresses")
    values = []
    for item in raw:
        value = str(item).strip().lower()
        if len(value) != 42 or not value.startswith("0x") or any(char not in "0123456789abcdef" for char in value[2:]):
            raise Exception("invalid_address")
        values.append(value)
    return sorted(set(values))


def _strings(raw, maximum_items: int, maximum_length: int) -> typing.Sequence[str]:
    if not isinstance(raw, list) or len(raw) > maximum_items:
        raise Exception("invalid_string_list")
    values = [_bounded(str(item).strip().lower(), maximum_length) for item in raw]
    return sorted(set(item for item in values if item != ""))


def _decimal_strings(raw, maximum_items: int) -> typing.Sequence[str]:
    values = _strings(raw, maximum_items, 100)
    if any(not item.isdigit() for item in values):
        raise Exception("invalid_decimal_list")
    return sorted(set(str(int(item)) for item in values), key=lambda item: (len(item), item))


def _optional_decimal(raw) -> str:
    value = str(raw).strip()
    if value == "":
        return ""
    if not value.isdigit() or len(value) > 30:
        raise Exception("invalid_decimal")
    return str(int(value))


def _optional_timestamp(raw) -> str:
    value = str(raw).strip()
    if value == "":
        return ""
    if len(value) < 20 or len(value) > 35 or "T" not in value or not value.endswith("Z"):
        raise Exception("use_iso_8601_utc")
    return value


def _bounded(value: str, maximum: int) -> str:
    if len(value) > maximum or "\x00" in value:
        raise Exception("value_too_long")
    return value


def _canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _canonical_parts(parts: typing.Sequence[str]) -> str:
    return "".join(str(len(str(part))) + ":" + str(part) for part in parts)


def _sha256_parts(parts: typing.Sequence[str]) -> str:
    return _sha256(_canonical_parts(parts))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_digest(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)
