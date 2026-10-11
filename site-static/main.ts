import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { ExecutionResult, TransactionHashVariant, TransactionStatus } from "genlayer-js/types";
import "./styles.css";

const defaultContract = "0x1Ab8f1ed238FE9F06923c6D18C15f22a9197d36d" as `0x${string}`;
const defaultReceipt = "peg_443f8cba63e00ce90477";
const example = {
  governanceName: "Aave Governance",
  proposalId: "359",
  proposalUrl: "https://vote.onaave.com/proposal/?ipfsHash=0x5c6bcd27cc94e27f40112647e0fde323c17706ce82746008ceae9d707deb0208&proposalId=359",
  executionChainId: "1",
  executionTxHash: "0x7a41b0b367d7914389edfdf132c9031fb6379bb97e7b6b0139c02ffd087f1ded",
  executionTxUrl: "https://etherscan.io/tx/0x7a41b0b367d7914389edfdf132c9031fb6379bb97e7b6b0139c02ffd087f1ded",
  declaredActions: "Call claimRewardsOnBehalf() for Sablier Legacy v1.1 and distribute 895805689180182547296 wei of AAVE to sablier.eth.",
  sourceUrls: [
    "https://vote.onaave.com/proposal/?ipfsHash=0x5c6bcd27cc94e27f40112647e0fde323c17706ce82746008ceae9d707deb0208&proposalId=359",
    "https://etherscan.io/tx/0x7a41b0b367d7914389edfdf132c9031fb6379bb97e7b6b0139c02ffd087f1ded",
    "https://governance.aave.com/t/arfc-claiming-aave-rewards-for-the-sablier-legacy-v1-1-contract/21975",
    "https://github.com/klopp78/proposalproof-genlayer-app/blob/main/evidence/aave-359.md",
  ],
};

type Ethereum = { request(args: { method: string; params?: unknown[] }): Promise<unknown> };
declare global { interface Window { ethereum?: Ethereum } }
let wallet: `0x${string}` | null = null;
let sources = [...example.sourceUrls];
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const address = () => $("contract-address") as HTMLInputElement;
const setStatus = (text: string, busy = false) => { $("status").textContent = text; $("status-dot").className = busy ? "pulse" : "dot"; ["connect", "verify", "read", "latest"].forEach((id) => (($("" + id) as HTMLButtonElement).disabled = busy)); };
const short = (value: string, size = 6) => value.length > size * 2 + 3 ? `${value.slice(0, size)}…${value.slice(-size)}` : value;
const message = (error: unknown) => error instanceof Error ? error.message : String(error);
const contract = () => address().value.trim() as `0x${string}`;

function renderSources() {
  $("sources").innerHTML = "";
  sources.forEach((value, index) => {
    const row = document.createElement("div"); row.className = "source-row";
    row.innerHTML = `<b>${index + 1}</b><input aria-label="Evidence source ${index + 1}" type="url" value="${escapeHtml(value)}"><button aria-label="Remove source ${index + 1}">×</button>`;
    const input = row.querySelector("input")!;
    input.addEventListener("input", () => { sources[index] = input.value; updateSourceCount(); });
    row.querySelector("button")!.addEventListener("click", () => { sources.splice(index, 1); renderSources(); });
    $("sources").append(row);
  });
  updateSourceCount();
}
function updateSourceCount() { $("source-count").textContent = `${sources.filter(Boolean).length}/5 sources`; (($("add-source") as HTMLButtonElement)).disabled = sources.length >= 5; }
function escapeHtml(value: string) { const div = document.createElement("div"); div.textContent = value; return div.innerHTML; }
function loadExample() { (($("governance") as HTMLInputElement)).value = example.governanceName; (($("proposal-id") as HTMLInputElement)).value = example.proposalId; (($("proposal-url") as HTMLInputElement)).value = example.proposalUrl; (($("execution-chain-id") as HTMLInputElement)).value = example.executionChainId; (($("execution-tx-hash") as HTMLInputElement)).value = example.executionTxHash; (($("execution-url") as HTMLInputElement)).value = example.executionTxUrl; (($("actions") as HTMLTextAreaElement)).value = example.declaredActions; sources = [...example.sourceUrls]; renderSources(); }
function readInput() { return { governanceName: (($("governance") as HTMLInputElement)).value.trim(), proposalId: (($("proposal-id") as HTMLInputElement)).value.trim(), proposalUrl: (($("proposal-url") as HTMLInputElement)).value.trim(), executionChainId: (($("execution-chain-id") as HTMLInputElement)).value.trim(), executionTxHash: (($("execution-tx-hash") as HTMLInputElement)).value.trim(), executionTxUrl: (($("execution-url") as HTMLInputElement)).value.trim(), declaredActions: (($("actions") as HTMLTextAreaElement)).value.trim(), sourceUrls: sources.filter(Boolean) }; }
function explorer() { const value = contract(); $("explorer").setAttribute("href", `https://explorer-studio.genlayer.com/address/${value}`); $("short-address").textContent = short(value); }
function client(account?: `0x${string}`) { return createClient({ chain: studionet, account, provider: window.ethereum }); }
async function connect() { if (!window.ethereum) throw new Error("No browser wallet detected."); const accounts = await window.ethereum.request({ method: "eth_requestAccounts" }) as `0x${string}`[]; if (!accounts[0]) throw new Error("No wallet account returned."); wallet = accounts[0]; $("connect").textContent = short(wallet); setStatus(`Wallet connected: ${short(wallet)}`); return wallet; }
async function readContract(functionName: string, args: string[]) { const readClient = createClient({ chain: studionet }); const result = await readClient.readContract({ address: contract(), functionName, args, jsonSafeReturn: true, transactionHashVariant: TransactionHashVariant.LATEST_FINAL }); return typeof result === "string" ? result : JSON.stringify(result); }
function extractId(value: unknown): string { if (typeof value === "string") return value.match(/peg_[a-f0-9]{20}/)?.[0] ?? ""; if (value instanceof Uint8Array) return new TextDecoder().decode(value).match(/peg_[a-f0-9]{20}/)?.[0] ?? ""; if (value && typeof value === "object") for (const child of Object.values(value as Record<string, unknown>)) { const found = extractId(child); if (found) return found; } return ""; }
async function load(id?: string) { try { setStatus("Reading finalized assessment and evidence pack...", true); const assessmentId = id || (await readContract("get_latest_assessment_id", [])).replaceAll('"', ""); const value = await readContract("get_assessment", [assessmentId]); const evidence = await readContract("get_evidence_pack", [assessmentId]); const record = JSON.parse(value) as Record<string, unknown>; const pack = JSON.parse(evidence) as Record<string, unknown>; if (record.assessment_id !== assessmentId || pack.assessment_id !== assessmentId) throw new Error("Contract readback returned a mismatched assessment ID."); $("receipt-id").value = assessmentId; renderRecord(record); $("evidence-pack").textContent = JSON.stringify(pack, null, 2); setStatus(`SUCCESS: finalized assessment and evidence pack loaded for ${assessmentId}`); } catch (error) { setStatus(`FAILED: ${message(error)}`); } }
async function poll(id: string) { let last: unknown; for (let attempt = 1; attempt <= 20; attempt += 1) { try { const value = await readContract("get_assessment", [id]); const parsed = JSON.parse(value) as Record<string, unknown>; if (parsed.assessment_id !== id) throw new Error("mismatched assessment ID"); return; } catch (error) { last = error; if (attempt < 20) await new Promise((resolve) => setTimeout(resolve, 2500)); } } throw new Error(`Assessment readback timed out: ${message(last)}`); }
async function verify() { try { const input = readInput(); if (input.sourceUrls.length < 2) throw new Error("Provide at least two evidence sources."); const account = wallet || await connect(); setStatus("Submitting normalized execution identity to GenLayer...", true); const writeClient = client(account); await writeClient.connect("studionet"); const hash = await writeClient.writeContract({ address: contract(), functionName: "assess_execution", args: [input.governanceName, input.proposalId, input.proposalUrl, input.executionChainId, input.executionTxHash, input.executionTxUrl, input.declaredActions, input.sourceUrls], value: BigInt(0), leaderOnly: false }); setStatus(`Submitted ${short(hash, 12)}. Waiting for FINALIZED validator consensus...`, true); const receipt = await writeClient.waitForTransactionReceipt({ hash, status: TransactionStatus.FINALIZED, interval: 3000, retries: 120, fullTransaction: true } as never); if ((receipt as { txExecutionResultName?: string }).txExecutionResultName !== ExecutionResult.FINISHED_WITH_RETURN) throw new Error(`GenVM did not finish successfully (${(receipt as { txExecutionResultName?: string }).txExecutionResultName ?? "unknown"}).`); const id = extractId(receipt); if (!id) throw new Error("Finalized GenVM result did not return a peg_* ID."); setStatus(`GenVM succeeded. Polling exact LATEST_FINAL readback for ${id}...`, true); await poll(id); await load(id); } catch (error) { setStatus(`FAILED: ${message(error)}`); } }
function setCheck(id: string, textId: string, value: unknown) { const passed = value === true; $(id).className = passed ? "check yes" : "check"; $(id).textContent = passed ? "✓" : "·"; $(textId).textContent = passed ? "matched" : "not confirmed"; }
function renderRecord(record: Record<string, unknown>) { const decision = String(record.decision ?? "not loaded").replaceAll("_", " "); $("decision").textContent = decision; $("decision").className = `decision ${decision.replaceAll(" ", "-")}`; $("confidence").textContent = record.confidence == null ? "—" : `${record.confidence}%`; $("source-total").textContent = String(record.supporting_source_count ?? "—"); $("chain").textContent = String(record.execution_chain_id ?? "—"); $("receipt-proposal").textContent = String(record.proposal_id ?? "—"); $("executed").textContent = String(record.executed_at_utc ?? "—"); $("snapshot").textContent = short(String(record.semantic_snapshot_bundle_hash ?? "—"), 12); $("evidence-hash").textContent = short(String(record.evidence_pack_hash ?? "—"), 12); $("record-hash").textContent = short(String((record.accepted_write as Record<string, unknown> | undefined)?.record_hash ?? "—"), 12); setCheck("proposal-check", "proposal-text", record.proposal_match); setCheck("action-check", "action-text", record.action_match); setCheck("execution-check", "execution-text", record.execution_tx_match); $("record").textContent = JSON.stringify(record, null, 2); }

$("connect").addEventListener("click", () => connect().catch((error) => setStatus(message(error))));
$("load-example").addEventListener("click", loadExample);
$("add-source").addEventListener("click", () => { if (sources.length < 5) { sources.push(""); renderSources(); } });
$("verify").addEventListener("click", verify);
$("read").addEventListener("click", () => load((($("receipt-id") as HTMLInputElement)).value.trim()));
$("latest").addEventListener("click", () => load());
address().addEventListener("input", explorer);
($("receipt-id") as HTMLInputElement).value = defaultReceipt;
address().value = defaultContract;
loadExample(); explorer();
