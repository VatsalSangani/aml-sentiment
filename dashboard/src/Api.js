// ── API service — connects React to FastAPI backend ───────────
const BASE_URL = "http://13.134.107.196:8503";

// ── Analyze a transaction (live — calls GPT-4o-mini) ──────────
export async function analyzeTransaction(formData) {
  const res = await fetch(`${BASE_URL}/analyze`, {
    method : "POST",
    headers: { "Content-Type": "application/json" },
    body   : JSON.stringify({
      payment_format: formData.payment_format,
      amount        : parseFloat(formData.amount),
      from_bank     : formData.from_bank,
      to_bank       : formData.to_bank,
      currency      : formData.currency,
      fan_out       : parseInt(formData.fan_out),
      tx_velocity   : parseInt(formData.tx_velocity),
    })
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Analysis failed");
  }
  return res.json();
}

// ── Get pre-generated XAI reports ─────────────────────────────
export async function getReports() {
  const res = await fetch(`${BASE_URL}/reports`);
  if (!res.ok) throw new Error("Failed to load reports");
  return res.json();
}

// ── Get model performance stats ────────────────────────────────
export async function getStats() {
  const res = await fetch(`${BASE_URL}/stats`);
  if (!res.ok) throw new Error("Failed to load stats");
  return res.json();
}

// ── Health check ───────────────────────────────────────────────
export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

// ── XAI service status ─────────────────────────────────────────
export async function getXaiStatus() {
  const res = await fetch(`${BASE_URL}/xai/status`);
  if (!res.ok) throw new Error("Failed to get XAI status");
  return res.json();
}

// ── Unload XAI service ─────────────────────────────────────────
export async function unloadXai() {
  const res = await fetch(`${BASE_URL}/xai/unload`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to unload XAI service");
  return res.json();
}
