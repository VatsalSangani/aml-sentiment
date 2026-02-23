// ── API service — connects React to FastAPI backend ───────────
const BASE_URL = "http://localhost:8000";

// ── Analyze a transaction (live — calls Qwen) ─────────────────
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

// ── Qwen status ────────────────────────────────────────────────
export async function getQwenStatus() {
  const res = await fetch(`${BASE_URL}/qwen/status`);
  if (!res.ok) throw new Error("Failed to get Qwen status");
  return res.json();
}

// ── Unload Qwen (free VRAM) ────────────────────────────────────
export async function unloadQwen() {
  const res = await fetch(`${BASE_URL}/qwen/unload`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to unload Qwen");
  return res.json();
}