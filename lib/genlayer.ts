import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { ExecutionResult, TransactionHashVariant, TransactionStatus } from "genlayer-js/types";

declare global {
  interface Window {
    ethereum?: { request: (args: { method: string; params?: unknown[] }) => Promise<unknown> };
  }
}

export const CONTRACT_ADDRESS =
  (process.env.NEXT_PUBLIC_PROPOSAL_EXECUTION_GUARD_ADDRESS ??
    "0x1Ab8f1ed238FE9F06923c6D18C15f22a9197d36d") as `0x${string}`;

export type WalletAddress = `0x${string}`;

export type AssessmentInput = {
  walletAddress: WalletAddress;
  governanceName: string;
  proposalId: string;
  proposalUrl: string;
  executionChainId: string;
  executionTxHash: string;
  executionTxUrl: string;
  declaredActions: string;
  sourceUrls: string[];
  contractAddress?: `0x${string}`;
  onStatus?: (status: string) => void;
};

function client(walletAddress?: WalletAddress) {
  return createClient({
    chain: studionet,
    account: walletAddress,
    provider: typeof window !== "undefined" ? window.ethereum : undefined,
  });
}

function address(override?: `0x${string}`) {
  return override ?? CONTRACT_ADDRESS;
}

export async function assessExecution(input: AssessmentInput) {
  const writeClient = client(input.walletAddress);
  input.onStatus?.("Submitting transaction to GenLayer...");
  await writeClient.connect("studionet");
  const contractAddress = address(input.contractAddress);
  const hash = await writeClient.writeContract({
    address: contractAddress,
    functionName: "assess_execution",
    args: [
      input.governanceName,
      input.proposalId,
      input.proposalUrl,
      input.executionChainId,
      input.executionTxHash,
      input.executionTxUrl,
      input.declaredActions,
      input.sourceUrls,
    ],
    value: BigInt(0),
    leaderOnly: false,
  });
  input.onStatus?.(`Submitted ${hash}. Waiting for validator consensus and FINALIZED status...`);
  const receipt = await waitForConsensus(writeClient, hash);
  input.onStatus?.("GenVM finalized with FINISHED_WITH_RETURN. Polling exact assessment readback...");
  const assessmentId = extractId(receipt, /peg_[a-f0-9]{20}/);
  if (!assessmentId) throw new Error("Finalized GenVM execution did not return a peg_* assessment ID.");
  const record = await pollAssessment(assessmentId, contractAddress);
  input.onStatus?.(`Assessment ${assessmentId} read from LATEST_FINAL. Reading durable evidence pack...`);
  const evidence = await readEvidencePack(assessmentId, contractAddress);
  return { hash, assessmentId, record: record.value, evidence };
}

export async function readAssessment(assessmentId: string, contractAddress = CONTRACT_ADDRESS) {
  const value = await read("get_assessment", [assessmentId], contractAddress);
  return { id: assessmentId, value };
}

export async function readLatestAssessment(contractAddress = CONTRACT_ADDRESS) {
  const id = await read("get_latest_assessment_id", [], contractAddress);
  if (!id) throw new Error("The contract has no accepted assessments yet.");
  return readAssessment(id.replaceAll('"', ""), contractAddress);
}

export async function readEvidencePack(assessmentId: string, contractAddress = CONTRACT_ADDRESS) {
  const value = await read("get_evidence_pack", [assessmentId], contractAddress);
  const parsed = parseJsonRecord(value, "evidence pack");
  if (parsed.assessment_id !== assessmentId) throw new Error("Evidence pack ID does not match the requested assessment.");
  return value;
}

async function read(functionName: string, args: string[], contractAddress: `0x${string}`) {
  const readClient = createClient({ chain: studionet });
  let lastError: unknown;
  try {
    const result = await readClient.readContract({
      address: contractAddress,
      functionName,
      args,
      jsonSafeReturn: true,
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return typeof result === "string" ? result : JSON.stringify(result);
  } catch (error) {
    lastError = error;
  }
  throw new Error(lastError instanceof Error ? lastError.message : String(lastError));
}

async function waitForConsensus(writeClient: ReturnType<typeof client>, hash: `0x${string}`) {
  const receipt = await writeClient.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.FINALIZED,
    interval: 3000,
    retries: 120,
    fullTransaction: true,
  } as never);
  assertSuccess(receipt);
  return receipt;
}

function assertSuccess(receipt: unknown) {
  const result = (receipt as { txExecutionResultName?: string })?.txExecutionResultName;
  if (result !== ExecutionResult.FINISHED_WITH_RETURN) {
    throw new Error(`Finalized GenVM execution was not successful (${result ?? "unknown"}).`);
  }
}

async function pollAssessment(assessmentId: string, contractAddress: `0x${string}`) {
  let lastError: unknown;
  for (let attempt = 1; attempt <= 20; attempt += 1) {
    try {
      const record = await readAssessment(assessmentId, contractAddress);
      const parsed = parseJsonRecord(record.value, "assessment");
      if (parsed.assessment_id !== assessmentId) throw new Error("Assessment readback returned a mismatched ID.");
      return record;
    } catch (error) {
      lastError = error;
      if (attempt < 20) await new Promise((resolve) => setTimeout(resolve, 2500));
    }
  }
  throw new Error(`Finalized assessment was not readable before timeout: ${lastError instanceof Error ? lastError.message : String(lastError)}`);
}

function parseJsonRecord(value: string, label: string) {
  if (!value || value === '""') throw new Error(`The ${label} readback was empty.`);
  try {
    const parsed = JSON.parse(value) as Record<string, unknown>;
    if (!parsed || typeof parsed !== "object") throw new Error("not an object");
    return parsed;
  } catch (error) {
    throw new Error(`The ${label} readback was not valid JSON: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function extractId(value: unknown, pattern: RegExp): string {
  if (typeof value === "string") return value.match(pattern)?.[0] ?? "";
  if (value instanceof Uint8Array) return new TextDecoder().decode(value).match(pattern)?.[0] ?? "";
  if (!value || typeof value !== "object") return "";
  for (const child of Object.values(value as Record<string, unknown>)) {
    const found = extractId(child, pattern);
    if (found) return found;
  }
  return "";
}
