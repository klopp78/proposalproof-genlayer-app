import importlib.util
import json
import pathlib
import sys
import types
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TX_HASH = "0x" + "7a" * 32
DESTINATION = "0x" + "12" * 20


class Generic:
    @classmethod
    def __class_getitem__(cls, _item):
        return cls


class Return:
    def __init__(self, calldata):
        self.calldata = calldata


class FakePublic:
    @staticmethod
    def view(function):
        return function

    @staticmethod
    def write(function):
        return function


class FakeWeb:
    @staticmethod
    def render(url, mode="text"):
        return f"Authoritative rendered evidence for {url}. " * 4


class FakeNondet:
    web = FakeWeb()

    @staticmethod
    def exec_prompt(prompt):
        if "Extract only decision-critical" in prompt:
            if "Source role: proposal" in prompt:
                return json.dumps({
                    "proposal_id": "359", "proposal_status": "passed", "chain_id": "",
                    "tx_hash": "", "execution_status": "unknown", "destination_addresses": [],
                    "function_calls": [], "values_wei": [], "parameters_canonical": "",
                    "block_number": "", "executed_at_utc": "",
                    "supports_declared_actions": True,
                    "supports_proposal_execution_link": True,
                })
            if "Source role: execution" in prompt:
                return json.dumps({
                    "proposal_id": "", "proposal_status": "unknown", "chain_id": "1",
                    "tx_hash": TX_HASH, "execution_status": "success",
                    "destination_addresses": [DESTINATION],
                    "function_calls": ["claimrewardsonbehalf()"], "values_wei": ["0"],
                    "parameters_canonical": "recipient=sablier.eth;amount=895805689180182547296",
                    "block_number": "23456789", "executed_at_utc": "2026-09-01T00:00:00Z",
                    "supports_declared_actions": True,
                    "supports_proposal_execution_link": True,
                })
            return json.dumps({
                "proposal_id": "359", "proposal_status": "passed", "chain_id": "1",
                "tx_hash": TX_HASH, "execution_status": "success",
                "destination_addresses": [DESTINATION],
                "function_calls": ["claimrewardsonbehalf()"], "values_wei": ["0"],
                "parameters_canonical": "recipient=sablier.eth;amount=895805689180182547296",
                "block_number": "23456789", "executed_at_utc": "2026-09-01T00:00:00Z",
                "supports_declared_actions": True,
                "supports_proposal_execution_link": True,
            })
        return json.dumps({
            "decision": "executed_match", "proposal_status": "passed",
            "execution_status": "success", "confidence": 94, "proposal_match": True,
            "action_match": True, "execution_tx_match": True,
            "executed_at_utc": "2026-09-01T00:00:00Z",
            "destination_addresses": [DESTINATION],
            "function_calls": ["claimrewardsonbehalf()"], "values_wei": ["0"],
            "parameters_canonical": "recipient=sablier.eth;amount=895805689180182547296",
            "block_number": "23456789", "supporting_source_count": 3,
        })


class FakeVM:
    Return = Return

    @staticmethod
    def run_nondet_unsafe(leader, validator):
        raw = leader()
        if not validator(Return(raw)):
            raise RuntimeError("validator rejected leader result")
        return raw


def load_contract():
    fake = types.ModuleType("genlayer")
    fake.gl = types.SimpleNamespace(
        Contract=object,
        public=FakePublic(),
        vm=FakeVM(),
        nondet=FakeNondet(),
        message=types.SimpleNamespace(sender_address="0x" + "ab" * 20),
    )
    fake.u64 = int
    fake.DynArray = Generic
    fake.TreeMap = Generic
    sys.modules["genlayer"] = fake
    spec = importlib.util.spec_from_file_location(
        "proposal_execution_guard", ROOT / "contracts" / "proposal_execution_guard.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContractBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract_module = load_contract()

    def test_normalized_execution_identity_rejects_url_aliasing(self):
        module = self.contract_module
        self.assertEqual(module._execution_id("1", TX_HASH), f"1:{TX_HASH}")
        with self.assertRaisesRegex(Exception, "execution_url_must_bind"):
            module._execution_url("https://etherscan.io/tx/0x" + "00" * 32, "1", TX_HASH)

    def test_provider_families_are_not_counted_as_independent_hosts(self):
        module = self.contract_module
        self.assertEqual(module._independence_key("etherscan.io"), "etherscan")
        self.assertEqual(module._independence_key("optimistic.etherscan.io"), "etherscan")
        self.assertEqual(module._independence_key("raw.githubusercontent.com"), "github")
        self.assertEqual(module._independence_key("github.com"), "github")

    def test_irrelevant_snapshot_changes_do_not_split_consensus(self):
        module = self.contract_module
        urls = ["https://vote.onaave.com/proposal/359", f"https://etherscan.io/tx/{TX_HASH}"]
        manifest = module._source_manifest(urls, urls[0], urls[1])
        raw = module._evaluate_execution(
            "Aave Governance", "359", urls[0], "1", TX_HASH, urls[1],
            "Call claimRewardsOnBehalf() for Sablier", urls, manifest, "a" * 64,
        )
        base = module._parse_result(raw, require_evidence=True)
        changed = dict(base)
        changed["semantic_snapshot_hashes"] = ["f" * 64, "e" * 64]
        changed["semantic_snapshot_bundle_hash"] = "d" * 64
        changed["raw_snapshot_bundle_hash"] = "c" * 64
        changed["executed_at_utc"] = "2026-01-01T00:00:01Z"
        self.assertEqual(module._consensus_view(base), module._consensus_view(changed))

    def test_positive_match_requires_strict_critical_agreement(self):
        module = self.contract_module
        urls = ["https://vote.onaave.com/proposal/359", f"https://etherscan.io/tx/{TX_HASH}"]
        manifest = module._source_manifest(urls, urls[0], urls[1])
        base = module._parse_result(module._evaluate_execution(
            "Aave Governance", "359", urls[0], "1", TX_HASH, urls[1],
            "Call claimRewardsOnBehalf() for Sablier", urls, manifest, "a" * 64,
        ), require_evidence=True)
        changed = dict(base)
        changed["values_wei"] = ["1"]
        self.assertNotEqual(module._consensus_view(base), module._consensus_view(changed))

    def test_conservative_non_matches_share_a_safe_consensus_view(self):
        module = self.contract_module
        base = {
            "assessment_context_hash": "a" * 64,
            "normalized_execution_identity": f"1:{TX_HASH}",
            "decision": "disputed",
        }
        changed = dict(base)
        changed["decision"] = "insufficient_evidence"
        self.assertEqual(module._consensus_view(base), module._consensus_view(changed))

    def test_validator_accepts_safe_negative_but_never_unverified_positive(self):
        module = self.contract_module
        identity = f"1:{TX_HASH}"
        negative = {
            "assessment_context_hash": "a" * 64,
            "normalized_execution_identity": identity,
            "decision": "disputed",
        }
        positive = dict(negative)
        positive["decision"] = "executed_match"
        positive.update({
            "proposal_status": "passed", "execution_status": "success",
            "proposal_match": True, "action_match": True, "execution_tx_match": True,
            "destination_addresses": [], "function_calls": [], "values_wei": [],
            "parameters_hash": "b" * 64, "block_number": "1",
            "supporting_source_count": 2, "independent_source_count": 2,
        })
        self.assertTrue(module._validator_agrees(negative, positive))
        self.assertFalse(module._validator_agrees(positive, negative))

    def test_adversarial_identity_mismatch_cannot_be_an_executed_match(self):
        module = self.contract_module
        original = FakeNondet.exec_prompt

        def mismatched(prompt):
            result = json.loads(original(prompt))
            if "Extract only decision-critical" in prompt and "Source role: execution" in prompt:
                result["tx_hash"] = "0x" + "99" * 32
            return json.dumps(result)

        FakeNondet.exec_prompt = staticmethod(mismatched)
        try:
            result = json.loads(module._evaluate_execution(
                "Aave Governance", "359", "https://vote.onaave.com/proposal/359", "1", TX_HASH,
                f"https://etherscan.io/tx/{TX_HASH}", "claimRewardsOnBehalf()",
                ["https://vote.onaave.com/proposal/359", f"https://etherscan.io/tx/{TX_HASH}"],
                module._source_manifest(
                    ["https://vote.onaave.com/proposal/359", f"https://etherscan.io/tx/{TX_HASH}"],
                    "https://vote.onaave.com/proposal/359", f"https://etherscan.io/tx/{TX_HASH}",
                ), "a" * 64,
            ))
            self.assertEqual(result["decision"], "disputed")
            self.assertFalse(result["execution_tx_match"])
        finally:
            FakeNondet.exec_prompt = staticmethod(original)

    def test_full_genvm_leader_validator_write_and_evidence_readback(self):
        module = self.contract_module
        contract = module.ProposalExecutionGuard()
        contract.assessment_ids = []
        contract.assessments = {}
        contract.evidence_packs = {}
        contract.claimed_executions = {}
        proposal_url = "https://vote.onaave.com/proposal/359"
        execution_url = f"https://etherscan.io/tx/{TX_HASH}"
        assessment_id = contract.assess_execution(
            "Aave Governance", "359", proposal_url, "1", TX_HASH, execution_url,
            "Call claimRewardsOnBehalf() for Sablier", [
                proposal_url, execution_url, "https://governance.aave.com/thread/359",
            ],
        )
        record = json.loads(contract.get_assessment(assessment_id))
        evidence = json.loads(contract.get_evidence_pack(assessment_id))
        self.assertEqual(record["decision"], "executed_match")
        self.assertEqual(record["execution_id"], f"1:{TX_HASH}")
        self.assertEqual(evidence["assessment_id"], assessment_id)
        self.assertEqual(len(evidence["snapshots"]), 3)
        self.assertEqual(contract.get_execution_claim("1", TX_HASH), assessment_id)
        with self.assertRaisesRegex(Exception, "execution_already_claimed"):
            contract.assess_execution(
                "Aave Governance", "359", proposal_url, "1", TX_HASH, execution_url,
                "Call claimRewardsOnBehalf() for Sablier", [proposal_url, execution_url],
            )


if __name__ == "__main__":
    unittest.main()
