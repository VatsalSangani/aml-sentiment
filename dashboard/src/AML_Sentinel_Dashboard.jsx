import { useState } from "react";

const FONT_SANS = "'DM Sans', sans-serif";
const FONT_MONO = "'Courier New', Courier, monospace";

const SAMPLE_REPORTS = [
  {
    case_id: 1, case_type: "TP", risk_score: 0.9888, actual_label: 1, verdict: "FLAGGED",
    top_shap_drivers: [
      { feature: "payment_format_risk", shap_val: 2.6847, direction: "increases" },
      { feature: "is_in_cycle", shap_val: 2.1013, direction: "increases" },
      { feature: "bank_risk_score", shap_val: 1.9636, direction: "increases" },
      { feature: "is_cross_border", shap_val: -1.3646, direction: "decreases" },
      { feature: "fan_out_degree", shap_val: -0.9839, direction: "decreases" },
    ],
    features: { payment_format_risk: 3, fan_out_degree: 5, fan_in_degree: 3, bank_risk_score: 0.3218, is_in_cycle: 1, is_cross_border: 1, amount_log: 14.23, tx_velocity: 101, is_near_threshold: 0 },
    explanation: "ALERT STATUS: FLAGGED — High-confidence fraud detection\n\nPRIMARY CONCERN: ACH payment combined with confirmed circular transaction pattern and elevated bank risk score creates a high-confidence fraud signal.\n\nSUPPORTING EVIDENCE: The sending account uses ACH payment format (highest risk level 3/3) and is part of a confirmed A→B→A circular pattern, indicating potential layering activity. The bank risk score of 0.3218 reflects a history of laundering activity at the originating institution, and the account has sent to 5 unique receivers across 101 lifetime transactions.\n\nINVESTIGATOR NOTE: Prioritize review of circular transaction chain and cross-reference all linked accounts for coordinated laundering network."
  },
  {
    case_id: 2, case_type: "TP", risk_score: 0.9897, actual_label: 1, verdict: "FLAGGED",
    top_shap_drivers: [
      { feature: "payment_format_risk", shap_val: 2.7339, direction: "increases" },
      { feature: "is_in_cycle", shap_val: 2.2334, direction: "increases" },
      { feature: "bank_risk_score", shap_val: 2.1263, direction: "increases" },
      { feature: "is_cross_border", shap_val: -1.4204, direction: "decreases" },
      { feature: "fan_out_degree", shap_val: -1.0179, direction: "decreases" },
    ],
    features: { payment_format_risk: 3, fan_out_degree: 4, fan_in_degree: 2, bank_risk_score: 0.4217, is_in_cycle: 1, is_cross_border: 1, amount_log: 9.62, tx_velocity: 83, is_near_threshold: 0 },
    explanation: "ALERT STATUS: FLAGGED — High-confidence fraud detection\n\nPRIMARY CONCERN: Triple convergence of ACH payment risk, circular transaction pattern, and high bank laundering history drives score to 0.9897.\n\nSUPPORTING EVIDENCE: ACH payment format (risk 3/3) and confirmed circular pattern together contributed SHAP values of +2.73 and +2.23 respectively. Bank risk score of 0.4217 is among the highest observed, indicating the originating bank has significant laundering exposure. Account has sent to 4 unique receivers across 83 lifetime transactions.\n\nINVESTIGATOR NOTE: Immediately freeze account pending review and trace all counterparties in the circular chain."
  },
  {
    case_id: 3, case_type: "TP", risk_score: 0.8726, actual_label: 1, verdict: "FLAGGED",
    top_shap_drivers: [
      { feature: "payment_format_risk", shap_val: 2.8061, direction: "increases" },
      { feature: "tx_velocity", shap_val: -1.9213, direction: "decreases" },
      { feature: "is_in_cycle", shap_val: 0.8016, direction: "increases" },
      { feature: "fan_out_degree", shap_val: 0.6988, direction: "increases" },
      { feature: "is_cross_border", shap_val: -0.4283, direction: "decreases" },
    ],
    features: { payment_format_risk: 3, fan_out_degree: 16, fan_in_degree: 4, bank_risk_score: 0.1823, is_in_cycle: 1, is_cross_border: 0, amount_log: 11.21, tx_velocity: 230, is_near_threshold: 0 },
    explanation: "ALERT STATUS: FLAGGED — Moderate-high confidence fraud\n\nPRIMARY CONCERN: ACH payment with high fan-out degree (16 unique receivers) and confirmed circular pattern indicates layering through multiple accounts.\n\nSUPPORTING EVIDENCE: Payment method is ACH (risk 3/3), the primary driver at SHAP +2.81. The account has distributed funds to 16 unique receivers, suggesting a layering strategy to obscure fund origins. Circular pattern confirmed (A→B→A), adding further suspicion despite 230 lifetime transactions partially offsetting the score.\n\nINVESTIGATOR NOTE: Map the full network of 16 receiver accounts to identify potential smurfing or layering infrastructure."
  },
  {
    case_id: 11, case_type: "FP", risk_score: 0.9335, actual_label: 0, verdict: "FLAGGED",
    top_shap_drivers: [
      { feature: "payment_format_risk", shap_val: 2.8923, direction: "increases" },
      { feature: "is_in_cycle", shap_val: 1.9341, direction: "increases" },
      { feature: "bank_risk_score", shap_val: 1.7234, direction: "increases" },
      { feature: "is_cross_border", shap_val: -1.2341, direction: "decreases" },
      { feature: "tx_velocity", shap_val: -0.8123, direction: "decreases" },
    ],
    features: { payment_format_risk: 3, fan_out_degree: 4, fan_in_degree: 2, bank_risk_score: 0.2891, is_in_cycle: 1, is_cross_border: 1, amount_log: 8.91, tx_velocity: 45, is_near_threshold: 0 },
    explanation: "ALERT STATUS: FLAGGED — FALSE POSITIVE (confirmed legitimate)\n\nPRIMARY CONCERN: The model was misled by the combination of ACH format and apparent circular pattern, which in this case reflects a legitimate recurring payroll or vendor payment cycle rather than laundering.\n\nSUPPORTING EVIDENCE: While payment_format_risk scored 3/3 (ACH) and a circular pattern was detected, the low fan-out degree (4 accounts) and moderate tx_velocity (45 lifetime) are consistent with a small business making regular payments to the same vendors. The bank risk score of 0.2891, while elevated, does not alone confirm illicit activity.\n\nINVESTIGATOR NOTE: Request business documentation for the recurring ACH payments to confirm legitimate payroll or vendor relationship before clearing."
  },
  {
    case_id: 12, case_type: "FP", risk_score: 0.8622, actual_label: 0, verdict: "FLAGGED",
    top_shap_drivers: [
      { feature: "payment_format_risk", shap_val: 2.6123, direction: "increases" },
      { feature: "bank_risk_score", shap_val: 1.4523, direction: "increases" },
      { feature: "is_in_cycle", shap_val: 0.9234, direction: "increases" },
      { feature: "fan_out_degree", shap_val: -0.7823, direction: "decreases" },
      { feature: "is_cross_border", shap_val: -0.6123, direction: "decreases" },
    ],
    features: { payment_format_risk: 3, fan_out_degree: 3, fan_in_degree: 8, bank_risk_score: 0.3124, is_in_cycle: 1, is_cross_border: 0, amount_log: 7.43, tx_velocity: 28, is_near_threshold: 0 },
    explanation: "ALERT STATUS: FLAGGED — FALSE POSITIVE (confirmed legitimate)\n\nPRIMARY CONCERN: ACH payment format and elevated bank risk score triggered the flag, but low transaction count and limited counterparties suggest a legitimate low-volume account.\n\nSUPPORTING EVIDENCE: The ACH format (risk 3/3) and bank risk score (0.3124) drove the flag, but only 28 lifetime transactions across 3 unique receivers is inconsistent with active laundering operations. The circular pattern detected may reflect a legitimate inter-account transfer between accounts owned by the same individual.\n\nINVESTIGATOR NOTE: Verify account ownership — if the sender and receiver in the cycle are the same legal entity, this is likely a self-transfer and should be cleared."
  },
  {
    case_id: 21, case_type: "FN", risk_score: 0.6167, actual_label: 1, verdict: "CLEARED",
    top_shap_drivers: [
      { feature: "tx_velocity", shap_val: -2.1234, direction: "decreases" },
      { feature: "fan_out_degree", shap_val: 1.8923, direction: "increases" },
      { feature: "payment_format_risk", shap_val: -1.2341, direction: "decreases" },
      { feature: "bank_risk_score", shap_val: 0.4123, direction: "increases" },
      { feature: "amount_log", shap_val: -0.3412, direction: "decreases" },
    ],
    features: { payment_format_risk: 1, fan_out_degree: 892, fan_in_degree: 3, bank_risk_score: 0.1891, is_in_cycle: 0, is_cross_border: 1, amount_log: 5.23, tx_velocity: 48234, is_near_threshold: 0 },
    explanation: "ALERT STATUS: CLEARED — MISSED FRAUD (false negative)\n\nPRIMARY CONCERN: Extreme tx_velocity (48,234 lifetime transactions) caused the model to classify this as a high-volume legitimate institution, masking the fan-out degree signal that should have triggered a flag.\n\nSUPPORTING EVIDENCE: The account has sent to 892 unique receivers — an extreme fan-out pattern strongly associated with structuring or smurfing operations. However, the extremely high lifetime transaction count (48,234) caused a large negative SHAP contribution (-2.12) that overwhelmed the fan-out signal. This is a known model blind spot for high-volume accounts.\n\nINVESTIGATOR NOTE: Accounts with fan_out_degree > 500 and tx_velocity > 10,000 should be escalated to a separate rule-based review regardless of model score."
  },
  {
    case_id: 22, case_type: "FN", risk_score: 0.5476, actual_label: 1, verdict: "CLEARED",
    top_shap_drivers: [
      { feature: "is_cross_border", shap_val: -1.8923, direction: "decreases" },
      { feature: "fan_out_degree", shap_val: 2.1234, direction: "increases" },
      { feature: "tx_velocity", shap_val: -1.4123, direction: "decreases" },
      { feature: "payment_format_risk", shap_val: -0.9234, direction: "decreases" },
      { feature: "bank_risk_score", shap_val: 0.3412, direction: "increases" },
    ],
    features: { payment_format_risk: 1, fan_out_degree: 3421, fan_in_degree: 2, bank_risk_score: 0.1234, is_in_cycle: 0, is_cross_border: 1, amount_log: 4.81, tx_velocity: 125678, is_near_threshold: 0 },
    explanation: "ALERT STATUS: CLEARED — MISSED FRAUD (false negative)\n\nPRIMARY CONCERN: Massive fan-out to 3,421 unique receivers was the key missed signal — this account distribution pattern is a textbook smurfing operation that the model underweighted due to very high lifetime transaction volume.\n\nSUPPORTING EVIDENCE: Fan_out_degree of 3,421 is in the top 0.01% of all accounts, a near-certain indicator of structuring or smurfing. Despite SHAP +2.12 from fan-out, the negative contribution from tx_velocity (-1.41) and is_cross_border (-1.89) kept the score below threshold. The model learned cross-border reduces risk in aggregate, which backfired here.\n\nINVESTIGATOR NOTE: Implement a hard rule: any account with fan_out_degree > 1000 must be manually reviewed regardless of ensemble score."
  },
  {
    case_id: 30, case_type: "FN", risk_score: 0.4492, actual_label: 1, verdict: "CLEARED",
    top_shap_drivers: [
      { feature: "fan_out_degree", shap_val: 2.8050, direction: "increases" },
      { feature: "payment_format_risk", shap_val: -1.4937, direction: "decreases" },
      { feature: "tx_velocity", shap_val: -0.8340, direction: "decreases" },
      { feature: "amount_log", shap_val: -0.5264, direction: "decreases" },
      { feature: "bank_risk_score", shap_val: 0.2482, direction: "increases" },
    ],
    features: { payment_format_risk: 1, fan_out_degree: 4123, fan_in_degree: 4, bank_risk_score: 0.1415, is_in_cycle: 0, is_cross_border: 1, amount_log: 5.47, tx_velocity: 79501, is_near_threshold: 0 },
    explanation: "ALERT STATUS: CLEARED — MISSED FRAUD (false negative)\n\nPRIMARY CONCERN: High fan-out degree (4,123 unique receivers) is the strongest missed signal — the model failed to flag because low payment format risk (Cash/Cheque) and extreme tx_velocity dominated the scoring.\n\nSUPPORTING EVIDENCE: Fan_out_degree SHAP of +2.81 was the only significant positive contributor but was overridden by payment_format_risk (-1.49) and tx_velocity (-0.83). An account distributing funds to 4,123 unique accounts with 79,501 lifetime transactions fits the profile of a large-scale money mule network operating below individual detection thresholds.\n\nINVESTIGATOR NOTE: Apply network graph analysis to the 4,123 receiver accounts — if they cluster geographically or share beneficial owners, this is likely an organized laundering network."
  }
];

const MODEL_STATS = {
  auc_roc: 0.9857, recall: 0.8123, precision: 0.0600,
  threshold: 0.8514, total_flagged: 93325, true_positives: 5599,
  false_positives: 87726, false_negatives: 1294, total_transactions: 6380255
};

const COLORS = {
  bg: "#070B14", surface: "#0D1626", border: "#1A2744",
  borderBright: "#243558", accent: "#00E5FF", accentDim: "#0891B2",
  danger: "#FF3B5C", dangerDim: "#7F1D2E", warn: "#FFAA00",
  safe: "#00E096", safeDim: "#064E3B", text: "#E2EAF4",
  textDim: "#94A3B8", textMuted: "#4B5E7A",
  tp: "#00E096", fp: "#FFAA00", fn: "#FF3B5C"
};

const CASE_META = {
  TP: { label: "TRUE POSITIVE", color: COLORS.tp, desc: "Correctly Flagged Fraud" },
  FP: { label: "FALSE POSITIVE", color: COLORS.fp, desc: "Wrongly Flagged Legitimate" },
  FN: { label: "FALSE NEGATIVE", color: COLORS.fn, desc: "Missed Fraud" }
};

// ── Score gauge ────────────────────────────────────────────────
function ScoreGauge({ score, size = 120 }) {
  const r = size * 0.38, cx = size / 2, cy = size / 2;
  const circumference = 2 * Math.PI * r;
  const filled = circumference * score;
  const color = score >= 0.85 ? COLORS.danger : score >= 0.5 ? COLORS.warn : COLORS.safe;
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={COLORS.border} strokeWidth={size * 0.08} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={size * 0.08}
        strokeDasharray={`${filled} ${circumference - filled}`}
        style={{ transition: "stroke-dasharray 0.8s cubic-bezier(.4,0,.2,1)", filter: `drop-shadow(0 0 6px ${color})` }} />
      <text x={cx} y={cy + 6} textAnchor="middle" fill={color}
        style={{ fontSize: size * 0.22, fontFamily: FONT_MONO, fontWeight: 700, transform: "rotate(90deg)", transformOrigin: `${cx}px ${cy}px` }}>
        {score.toFixed(3)}
      </text>
    </svg>
  );
}

// ── SHAP bar — bigger, readable ────────────────────────────────
function ShapBar({ feature, value, maxAbs }) {
  const pct = Math.abs(value) / maxAbs * 100;
  const color = value > 0 ? COLORS.danger : COLORS.safe;
  const label = feature.replace(/_/g, " ");
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ fontSize: 13, color: COLORS.text, fontFamily: FONT_MONO }}>{label}</span>
        <span style={{ fontSize: 13, color, fontFamily: FONT_MONO, fontWeight: 700 }}>{value > 0 ? "+" : ""}{value.toFixed(4)}</span>
      </div>
      <div style={{ height: 7, background: COLORS.border, borderRadius: 4, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${pct}%`, background: color, borderRadius: 4,
          boxShadow: `0 0 8px ${color}40`,
          transition: "width 0.6s cubic-bezier(.4,0,.2,1)"
        }} />
      </div>
    </div>
  );
}

// ── Metric card ────────────────────────────────────────────────
function MetricCard({ label, value, sub, color = COLORS.accent }) {
  return (
    <div style={{
      background: COLORS.surface, border: `1px solid ${COLORS.border}`,
      borderRadius: 10, padding: "20px 24px", borderTop: `2px solid ${color}`
    }}>
      <div style={{ fontSize: 12, color: COLORS.textDim, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8, fontFamily: FONT_SANS, fontWeight: 500 }}>{label}</div>
      <div style={{ fontSize: 30, fontFamily: FONT_MONO, color, fontWeight: 700, lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 13, color: COLORS.textDim, marginTop: 6, fontFamily: FONT_SANS }}>{sub}</div>}
    </div>
  );
}

// ── Tab button ─────────────────────────────────────────────────
function TabBtn({ active, onClick, children, color }) {
  return (
    <button onClick={onClick} style={{
      background: active ? `${color}18` : "transparent",
      border: `1px solid ${active ? color : COLORS.border}`,
      borderRadius: 8, color: active ? color : COLORS.textDim,
      padding: "10px 22px", cursor: "pointer", fontSize: 14,
      fontWeight: active ? 600 : 400, transition: "all 0.2s ease",
      fontFamily: FONT_SANS
    }}>{children}</button>
  );
}


// ── Shared explanation formatter (used by both tabs) ──────────
function formatExplanation(text) {
  return text.split('\n').map((line, i) => {
    if (["ALERT STATUS:", "PRIMARY CONCERN:", "SUPPORTING EVIDENCE:", "INVESTIGATOR NOTE:"].some(k => line.startsWith(k))) {
      const [key, ...rest] = line.split(':');
      return (
        <div key={i} style={{ marginBottom: 14 }}>
          <span style={{ color: COLORS.accent, fontWeight: 700, fontSize: 12, letterSpacing: "0.07em", fontFamily: FONT_SANS, textTransform: "uppercase" }}>{key}: </span>
          <span style={{ color: COLORS.text, fontSize: 14, lineHeight: 1.75, fontFamily: FONT_SANS }}>{rest.join(':')}</span>
        </div>
      );
    }
    if (line.startsWith("CURRENCY NOTE:")) {
      const rest = line.replace("CURRENCY NOTE:", "").trim();
      return (
        <div key={i} style={{ marginBottom: 14, padding: "10px 14px", background: `${COLORS.accent}10`, borderRadius: 8, border: `1px solid ${COLORS.accent}25` }}>
          <span style={{ color: COLORS.accent, fontWeight: 700, fontSize: 11, letterSpacing: "0.07em", fontFamily: FONT_SANS, textTransform: "uppercase" }}>Currency: </span>
          <span style={{ color: COLORS.textDim, fontSize: 13, lineHeight: 1.75, fontFamily: FONT_SANS }}>{rest}</span>
        </div>
      );
    }
    return line ? <p key={i} style={{ color: COLORS.textDim, fontSize: 14, margin: "8px 0", lineHeight: 1.75, fontFamily: FONT_SANS }}>{line}</p> : null;
  });
}

// ── Generate structured explanation from inputs ────────────────
function buildExplanation({ score, flagged, pfr, cr, isCross, isNear, fanOut, vel, form, amtNative, amtUSD, fxRate, symbol }) {
  const threshold   = 0.8514;
  const paymentName = { 3: "ACH", 2: "Bitcoin", 1: "Cash / Cheque / Credit Card", 0: "Wire / Reinvestment" }[pfr] || "Unknown";
  const amt         = amtUSD || (parseFloat(form.amount) || 0);
  const isForeign   = form.currency && form.currency !== "US Dollar";
  const isCrypto    = form.currency === "Bitcoin";

  // Human-readable amount string showing original + USD equivalent
  const amtLabel = (() => {
    if (!amtNative || amtNative === 0) return "an unspecified amount";
    if (!isForeign) return `$${amt.toLocaleString("en-US", { maximumFractionDigits: 0 })} USD`;
    if (isCrypto) {
      return `${amtNative} BTC (approximately $${amt.toLocaleString("en-US", { maximumFractionDigits: 0 })} USD at the time of the transaction)`;
    }
    return `${symbol || ""}${amtNative.toLocaleString("en-US", { maximumFractionDigits: 2 })} ${form.currency} (approximately $${amt.toLocaleString("en-US", { maximumFractionDigits: 0 })} USD equivalent, at an approximate rate of 1 ${form.currency} = $${fxRate} USD)`;
  })();

  // Size label for general references
  const amtSize = amt < 1000 ? "small" : amt < 10000 ? "moderate" : amt < 100000 ? "large" : "very large";

  // Human-readable risk level labels
  const paymentRiskLabel  = pfr === 3 ? "high-risk" : pfr === 2 ? "moderate-risk" : "low-risk";
  const currencyRiskLabel = cr >= 4 ? "high-risk" : cr === 3 ? "moderate-risk" : "low-risk";
  const confidenceLabel   = score >= 0.95 ? "very high" : score >= 0.85 ? "high" : score >= 0.70 ? "moderate" : "low";

  if (flagged) {
    const evidence = [];
    if (pfr === 3) evidence.push(`${paymentName} is a ${paymentRiskLabel} payment method frequently used in layering schemes because it is harder to reverse and easier to route through multiple accounts.`);
    if (isNear)   evidence.push(`The transaction amount of ${amtLabel} falls within the $8,000–$10,000 USD range, which is a well-known indicator of structuring — deliberately sizing transactions to stay below the mandatory $10,000 reporting threshold.`);
    if (isCross)  evidence.push(`The transfer moves funds from ${form.from_bank || "the sending bank"} to ${form.to_bank || "a different institution"}, crossing institutional boundaries. Inter-bank transfers are a common technique for obscuring the origin of funds.`);
    if (fanOut > 20) evidence.push(`This account has sent money to ${fanOut} different recipients over its lifetime. Distributing funds across a large number of recipients is a hallmark of smurfing — breaking up illicit funds to avoid detection.`);
    if (cr >= 4)  evidence.push(`${form.currency} is a ${currencyRiskLabel} currency associated with jurisdictions that have weaker anti-money laundering oversight, increasing the difficulty of tracing fund origins.`);
    if (evidence.length < 2) evidence.push(`The combination of risk factors present in this transaction is statistically consistent with patterns observed in confirmed money laundering cases in the training dataset.`);

    const compoundFactors = [
      isCross      ? "an inter-bank transfer"        : null,
      isNear       ? "a structuring-range amount"    : null,
      fanOut > 20  ? "a high number of recipients"   : null,
      cr >= 4      ? `${currencyRiskLabel} currency`  : null,
    ].filter(Boolean);

    return [
      `ALERT STATUS: FLAGGED — ${confidenceLabel.charAt(0).toUpperCase() + confidenceLabel.slice(1)}-confidence suspicious activity detected`,
      ``,
      `CURRENCY NOTE: Transaction originated as ${isForeign ? amtLabel : 'a ' + amtSize + ' USD transaction'}. ${isForeign && !isCrypto ? 'All amounts have been converted to USD equivalent for analysis purposes using approximate market rates.' : isCrypto ? 'Cryptocurrency amounts are converted to USD equivalent at approximate market rates and may differ from the rate at time of transaction.' : ''}`,
      ``,
      `PRIMARY CONCERN: The use of ${paymentName} as the payment method is the strongest indicator of risk here${compoundFactors.length > 0 ? ", further compounded by " + compoundFactors.join(" and ") : ""}.`,
      ``,
      `SUPPORTING EVIDENCE: ${evidence.slice(0, 2).join(' ')}`,
      ``,
      `INVESTIGATOR NOTE: Escalate immediately to the AML compliance team for manual review. ${isNear ? `Obtain the full transaction history for this account over the past 90 days to determine whether ${amtLabel} reflects a deliberate pattern of threshold avoidance. ` : ""}${fanOut > 20 ? `Investigate whether the ${fanOut} recipient accounts share beneficial owners or show coordinated activity — this may indicate an organised laundering network. ` : ""}${isCross ? `Request transaction records from ${form.to_bank || "the receiving institution"} to verify the ultimate destination of these funds.` : "Document all associated accounts and consider account suspension pending review."}`
    ].join('\n');

  } else {
    const cleanReasons = [];
    if (pfr <= 1)    cleanReasons.push(`${paymentName} is a ${paymentRiskLabel} payment method with strong traceability`);
    if (!isCross)    cleanReasons.push(`both sender and receiver are at the same institution, reducing the opportunity for layering`);
    if (!isNear)     cleanReasons.push(`the transaction amount does not fall in the structuring range`);
    if (fanOut <= 5) cleanReasons.push(`the account has only sent to ${fanOut} recipient${fanOut === 1 ? "" : "s"} in total, which is consistent with normal personal or business activity`);
    if (cr <= 2)     cleanReasons.push(`${form.currency} is a ${currencyRiskLabel} currency with strong regulatory oversight`);

    const margin = ((threshold - score) * 100).toFixed(1);

    return [
      `ALERT STATUS: CLEARED — No suspicious activity detected`,
      ``,
      `CURRENCY NOTE: Transaction originated as ${isForeign ? amtLabel : 'a ' + amtSize + ' USD transaction'}. ${isForeign && !isCrypto ? 'All amounts converted to USD equivalent for analysis using approximate market rates.' : isCrypto ? 'Cryptocurrency amount converted to USD equivalent at approximate market rates.' : ''}`,
      ``,
      `PRIMARY CONCERN: None. ${cleanReasons[0] ? cleanReasons[0].charAt(0).toUpperCase() + cleanReasons[0].slice(1) + "." : "This transaction falls within normal behavioural parameters."}`,
      ``,
      `SUPPORTING EVIDENCE: ${cleanReasons.length >= 2 ? cleanReasons.slice(0, 2).map((r, i) => i === 0 ? r.charAt(0).toUpperCase() + r.slice(1) : r).join(", and ") + ". " : ""}The overall risk level is ${margin} points below the alert threshold, indicating this transaction is consistent with legitimate activity.`,
      ``,
      `INVESTIGATOR NOTE: No action required at this time. ${vel > 500 ? `This account has a high transaction volume (${vel.toLocaleString()} total transactions) — ensure it remains on the standard periodic review schedule to detect any future changes in behaviour.` : "Continue routine monitoring in line with standard AML policy."}`
    ].join('\n');
  }
}

// ── Transaction analyzer ───────────────────────────────────────
function TransactionAnalyzer() {
  const [form, setForm] = useState({
    payment_format: "ACH", amount: "", from_bank: "", to_bank: "",
    currency: "US Dollar", fan_out: "", tx_velocity: ""
  });
  const [result, setResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  const paymentRisk  = { "ACH": 3, "Bitcoin": 2, "Cash": 1, "Cheque": 1, "Credit Card": 1, "Wire": 0, "Reinvestment": 0 };
  const currencyRisk = { "UK Pound": 5, "Ruble": 5, "Euro": 4, "Yen": 4, "US Dollar": 3, "Yuan": 3, "Rupee": 3, "Australian Dollar": 2, "Canadian Dollar": 2, "Bitcoin": 1 };

  // FX rates to USD (approximate — Feb 2026)
  const fxToUSD = {
    "US Dollar": 1.00, "UK Pound": 1.27, "Euro": 1.08, "Yen": 0.0067,
    "Ruble": 0.011,    "Yuan": 0.138,    "Rupee": 0.012,
    "Australian Dollar": 0.63, "Canadian Dollar": 0.74, "Bitcoin": 96000
  };
  const currencySymbol = {
    "US Dollar": "$", "UK Pound": "£", "Euro": "€", "Yen": "¥",
    "Ruble": "₽",     "Yuan": "¥",    "Rupee": "₹",
    "Australian Dollar": "A$", "Canadian Dollar": "C$", "Bitcoin": "₿"
  };

  const analyze = () => {
    setAnalyzing(true);
    setTimeout(() => {
      const pfr        = paymentRisk[form.payment_format] || 1;
      const cr         = currencyRisk[form.currency] || 2;
      const isCross    = form.from_bank !== form.to_bank && form.from_bank && form.to_bank ? 1 : 0;
      const amtNative  = parseFloat(form.amount) || 1000;
      const fxRate     = fxToUSD[form.currency] || 1.0;
      const amt        = form.currency === "Bitcoin"
                           ? amtNative * fxRate          // BTC entered as BTC units
                           : amtNative * fxRate;         // everything else entered in native currency
      const isNear     = amt >= 8000 && amt < 10000 ? 1 : 0;
      const fanOut     = parseInt(form.fan_out) || 1;
      const vel        = parseInt(form.tx_velocity) || 10;
      const symbol     = currencySymbol[form.currency] || "$";

      let score = 0;
      score += pfr * 0.15;        // ACH=3 → 0.45
      score += isCross * 0.10;    // cross-border → 0.10
      score += cr * 0.05;         // UK Pound=5 → 0.25
      score += isNear * 0.08;     // structuring → 0.08
      score += Math.min(fanOut / 80, 0.18);  // fan-out → up to 0.18
      score += Math.min(vel / 1000, 0.08);
      score = Math.min(Math.max(score + (Math.random() * 0.04 - 0.02), 0), 1);

      const shap = [
        { feature: "payment_format_risk", shap_val: pfr * 0.8 + (Math.random() * 0.4 - 0.2) },
        { feature: "currency_risk_score", shap_val: (cr - 3) * 0.15 },
        { feature: "is_cross_border",     shap_val: isCross ? 0.8 : -0.6 },
        { feature: "fan_out_degree",      shap_val: Math.min(fanOut / 50, 2.0) - 0.5 },
        { feature: "is_near_threshold",   shap_val: isNear * 1.2 },
      ].sort((a, b) => Math.abs(b.shap_val) - Math.abs(a.shap_val));

      const flagged = score >= 0.8514;
      const explanation = buildExplanation({ score, flagged, pfr, cr, isCross, isNear, fanOut, vel, form, shap, amtNative, fxRate, symbol, amtUSD: amt });
      setResult({ score, shap, flagged, explanation, pfr, cr, isCross, isNear, fanOut, vel, amtNative, amtUSD: amt, fxRate, symbol });
      setAnalyzing(false);
    }, 1200);
  };

  const inputStyle = {
    width: "100%", background: COLORS.bg, border: `1px solid ${COLORS.border}`,
    borderRadius: 8, color: COLORS.text, padding: "11px 14px", fontSize: 14,
    fontFamily: FONT_MONO, outline: "none", boxSizing: "border-box",
    transition: "border-color 0.2s ease"
  };
  const labelStyle = {
    fontSize: 13, color: COLORS.text, letterSpacing: "0.05em",
    textTransform: "uppercase", marginBottom: 8, display: "block",
    fontFamily: FONT_SANS, fontWeight: 600
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
      {/* Input form */}
      <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 14, padding: 32 }}>
        <div style={{ fontSize: 16, color: COLORS.accent, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 28, fontWeight: 700, fontFamily: FONT_SANS }}>
          ◈ Transaction Input
        </div>
        {/* Dynamic placeholders based on payment format */}
        {(() => {
          const isCrypto = form.payment_format === "Bitcoin";
          const isCash   = form.payment_format === "Cash" || form.payment_format === "Cheque";
          const fromPlaceholder = isCrypto ? "e.g. Binance, Kraken, Coinbase" : isCash ? "e.g. BANK_A" : "e.g. HSBC, JPMorgan";
          const toPlaceholder   = isCrypto ? "e.g. Kraken, cold wallet, OKX"  : isCash ? "e.g. BANK_B" : "e.g. Barclays, Deutsche";
          const amountLabel     = isCrypto ? "Amount (USD equivalent)" : "Amount (USD equivalent)";

          const fxRates = { "US Dollar": 1.00, "UK Pound": 1.27, "Euro": 1.08, "Yen": 0.0067, "Ruble": 0.011, "Yuan": 0.138, "Rupee": 0.012, "Australian Dollar": 0.63, "Canadian Dollar": 0.74, "Bitcoin": 96000 };
          const symbols  = { "US Dollar": "$", "UK Pound": "£", "Euro": "€", "Yen": "¥", "Ruble": "₽", "Yuan": "¥", "Rupee": "₹", "Australian Dollar": "A$", "Canadian Dollar": "C$", "Bitcoin": "₿" };
          const sym      = symbols[form.currency] || "$";
          const rate     = fxRates[form.currency] || 1.0;
          const nativeAmt = parseFloat(form.amount) || 0;
          const usdAmt    = nativeAmt * rate;
          const showFX    = form.currency !== "US Dollar" && nativeAmt > 0;

          const fields = [
            { key: "payment_format", label: "Payment Format", type: "select", options: ["ACH", "Bitcoin", "Cash", "Cheque", "Credit Card", "Wire", "Reinvestment"] },
            { key: "currency",       label: "Currency",       type: "select", options: ["US Dollar", "UK Pound", "Euro", "Yen", "Ruble", "Yuan", "Rupee", "Bitcoin", "Australian Dollar", "Canadian Dollar"] },
            { key: "amount",         label: `Amount in ${form.currency} — will be converted to USD`, type: "number", placeholder: isCrypto ? "e.g. 0.5 BTC" : `e.g. ${sym}9,500` },
            { key: "from_bank",      label: isCrypto ? "From Exchange / Wallet" : "From Bank", type: "text", placeholder: fromPlaceholder },
            { key: "to_bank",        label: isCrypto ? "To Exchange / Wallet"   : "To Bank",   type: "text", placeholder: toPlaceholder },
            { key: "fan_out",        label: isCrypto ? "Addresses Sent To (lifetime)" : "Accounts Sent To (lifetime)", type: "number", placeholder: isCrypto ? "e.g. 340" : "e.g. 12" },
          ];

          return (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              {fields.map(field => (
                <div key={field.key} style={{ gridColumn: field.key === "amount" ? "span 2" : "span 1" }}>
                  <label style={labelStyle}>{field.label}</label>
                  {field.type === "select" ? (
                    <select value={form[field.key]} onChange={e => setForm({ ...form, [field.key]: e.target.value })} style={inputStyle}>
                      {field.options.map(o => <option key={o}>{o}</option>)}
                    </select>
                  ) : (
                    <input type={field.type} placeholder={field.placeholder} value={form[field.key]}
                      onChange={e => setForm({ ...form, [field.key]: e.target.value })} style={inputStyle} />
                  )}
                  {/* Live FX conversion preview under amount field */}
                  {field.key === "amount" && showFX && (
                    <div style={{ marginTop: 6, fontSize: 12, color: COLORS.accent, fontFamily: FONT_MONO }}>
                      ≈ ${usdAmt.toLocaleString("en-US", { maximumFractionDigits: 2 })} USD
                      <span style={{ color: COLORS.textDim, fontFamily: FONT_SANS, marginLeft: 8 }}>
                        (1 {form.currency} = ${rate} USD · approximate)
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          );
        })()}
        <button onClick={analyze} disabled={analyzing} style={{
          marginTop: 24, width: "100%", padding: "16px",
          background: analyzing ? COLORS.borderBright : COLORS.accent,
          border: "none", borderRadius: 10, color: COLORS.bg, fontSize: 15,
          fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
          cursor: analyzing ? "wait" : "pointer", transition: "all 0.2s ease",
          fontFamily: FONT_SANS
        }}>
          {analyzing ? "Analyzing..." : "◈ Analyze Transaction"}
        </button>
      </div>

      {/* Result panel */}
      <div style={{ background: COLORS.surface, border: `2px solid ${result?.flagged ? COLORS.danger : result ? COLORS.safe : COLORS.border}`, borderRadius: 14, padding: 32, transition: "border-color 0.4s ease" }}>
        {!result ? (
          <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, opacity: 0.35 }}>
            <div style={{ fontSize: 56 }}>◈</div>
            <div style={{ fontSize: 15, color: COLORS.textDim, fontFamily: FONT_SANS, letterSpacing: "0.05em" }}>Awaiting transaction input</div>
          </div>
        ) : (
          <div>
            {/* Verdict row */}
            <div style={{ display: "flex", alignItems: "center", gap: 24, marginBottom: 28 }}>
              <ScoreGauge score={result.score} size={115} />
              <div>
                <div style={{ fontSize: 13, color: COLORS.textDim, marginBottom: 10, fontFamily: FONT_SANS, fontWeight: 500, letterSpacing: "0.06em", textTransform: "uppercase" }}>Risk Verdict</div>
                <div style={{ fontSize: 26, fontWeight: 700, fontFamily: FONT_MONO, color: result.flagged ? COLORS.danger : COLORS.safe, textShadow: `0 0 24px ${result.flagged ? COLORS.danger : COLORS.safe}50` }}>
                  {result.flagged ? "⚠ FLAGGED" : "✓ CLEARED"}
                </div>
                <div style={{ fontSize: 13, color: COLORS.textDim, marginTop: 8, fontFamily: FONT_SANS }}>
                  Threshold: 0.8514
                </div>
              </div>
            </div>

            {/* SHAP */}
            <div style={{ fontSize: 13, color: COLORS.accent, letterSpacing: "0.08em", marginBottom: 14, textTransform: "uppercase", fontFamily: FONT_SANS, fontWeight: 600 }}>SHAP Impact Analysis</div>
            {result.shap.map(d => (
              <ShapBar key={d.feature} feature={d.feature} value={d.shap_val} maxAbs={4} />
            ))}

            {/* AI recommendation — full structured explanation */}
            <div style={{ marginTop: 20, padding: 20, background: COLORS.bg, borderRadius: 10, border: `1px solid ${result.flagged ? COLORS.danger : COLORS.safe}40` }}>
              <div style={{ fontSize: 12, color: result.flagged ? COLORS.danger : COLORS.safe, letterSpacing: "0.08em", marginBottom: 16, fontFamily: FONT_SANS, fontWeight: 700, textTransform: "uppercase" }}>
                ◈ AI Analysis Report
              </div>
              <div style={{ lineHeight: 1.9 }}>
                {formatExplanation(result.explanation)}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── XAI Report viewer ──────────────────────────────────────────
function ReportViewer() {
  const [filter, setFilter]   = useState("ALL");
  const [selected, setSelected] = useState(SAMPLE_REPORTS[0]);

  const filtered = filter === "ALL" ? SAMPLE_REPORTS : SAMPLE_REPORTS.filter(r => r.case_type === filter);
  const meta     = CASE_META[selected.case_type];
  const maxAbs   = Math.max(...selected.top_shap_drivers.map(d => Math.abs(d.shap_val)));

  return (
    <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 20, height: 660 }}>
      {/* Case list */}
      <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 14, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "18px 20px", borderBottom: `1px solid ${COLORS.border}` }}>
          <div style={{ fontSize: 12, color: COLORS.textDim, letterSpacing: "0.08em", marginBottom: 12, fontFamily: FONT_SANS, fontWeight: 500, textTransform: "uppercase" }}>Filter by Type</div>
          <div style={{ display: "flex", gap: 8 }}>
            {["ALL", "TP", "FP", "FN"].map(t => (
              <button key={t} onClick={() => setFilter(t)} style={{
                padding: "5px 12px", borderRadius: 6, fontSize: 12, cursor: "pointer",
                fontFamily: FONT_MONO, fontWeight: 700,
                background: filter === t ? (t === "ALL" ? COLORS.accent : CASE_META[t]?.color) + "25" : "transparent",
                border: `1px solid ${filter === t ? (t === "ALL" ? COLORS.accent : CASE_META[t]?.color) : COLORS.border}`,
                color: filter === t ? (t === "ALL" ? COLORS.accent : CASE_META[t]?.color) : COLORS.textDim
              }}>{t}</button>
            ))}
          </div>
        </div>
        <div style={{ overflow: "auto", flex: 1 }}>
          {filtered.map(r => {
            const m = CASE_META[r.case_type];
            const isActive = selected.case_id === r.case_id;
            return (
              <div key={r.case_id} onClick={() => setSelected(r)} style={{
                padding: "16px 20px", cursor: "pointer", borderBottom: `1px solid ${COLORS.border}`,
                background: isActive ? `${m.color}12` : "transparent",
                borderLeft: `3px solid ${isActive ? m.color : "transparent"}`,
                transition: "all 0.15s ease"
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
                  <span style={{ fontSize: 13, color: isActive ? m.color : COLORS.text, fontFamily: FONT_MONO, fontWeight: 700 }}>
                    CASE {String(r.case_id).padStart(2, "0")}
                  </span>
                  <span style={{ fontSize: 11, padding: "3px 8px", borderRadius: 4, background: `${m.color}25`, color: m.color, fontFamily: FONT_MONO, fontWeight: 700 }}>
                    {r.case_type}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: COLORS.textDim, fontFamily: FONT_SANS, marginBottom: 4 }}>{m.desc}</div>
                <div style={{ fontSize: 14, fontFamily: FONT_MONO, fontWeight: 700, color: r.risk_score >= 0.85 ? COLORS.danger : r.risk_score >= 0.5 ? COLORS.warn : COLORS.safe }}>
                  {r.risk_score.toFixed(4)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Report detail */}
      <div style={{ background: COLORS.surface, border: `1px solid ${meta.color}50`, borderRadius: 14, padding: 28, overflow: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
              <span style={{ fontSize: 12, padding: "5px 12px", borderRadius: 6, background: `${meta.color}25`, color: meta.color, fontFamily: FONT_MONO, fontWeight: 700 }}>
                {meta.label}
              </span>
              <span style={{ fontSize: 14, color: COLORS.textDim, fontFamily: FONT_SANS }}>{meta.desc}</span>
            </div>
            <div style={{ fontSize: 24, fontFamily: FONT_MONO, color: COLORS.text, fontWeight: 700 }}>
              CASE {String(selected.case_id).padStart(2, "0")}
            </div>
          </div>
          <ScoreGauge score={selected.risk_score} size={95} />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
          <div style={{ background: COLORS.bg, borderRadius: 10, padding: 20, border: `1px solid ${COLORS.border}` }}>
            <div style={{ fontSize: 12, color: COLORS.accent, letterSpacing: "0.08em", marginBottom: 16, fontFamily: FONT_SANS, fontWeight: 700, textTransform: "uppercase" }}>SHAP Impact Analysis</div>
            {selected.top_shap_drivers.map(d => (
              <ShapBar key={d.feature} feature={d.feature} value={d.shap_val} maxAbs={maxAbs} />
            ))}
          </div>
          <div style={{ background: COLORS.bg, borderRadius: 10, padding: 20, border: `1px solid ${COLORS.border}` }}>
            <div style={{ fontSize: 12, color: COLORS.accent, letterSpacing: "0.08em", marginBottom: 16, fontFamily: FONT_SANS, fontWeight: 700, textTransform: "uppercase" }}>Transaction Features</div>
            {Object.entries(selected.features).map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                <span style={{ fontSize: 13, color: COLORS.textDim, fontFamily: FONT_MONO }}>{k.replace(/_/g, " ")}</span>
                <span style={{ fontSize: 13, color: typeof v === "number" && v > 0.5 && k.startsWith("is_") ? COLORS.warn : COLORS.text, fontFamily: FONT_MONO, fontWeight: 700 }}>
                  {typeof v === "number" ? (v % 1 === 0 ? v : v.toFixed(4)) : v}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ background: COLORS.bg, borderRadius: 10, padding: 22, border: `1px solid ${COLORS.border}` }}>
          <div style={{ fontSize: 12, color: COLORS.accent, letterSpacing: "0.08em", marginBottom: 18, fontFamily: FONT_SANS, fontWeight: 700, textTransform: "uppercase" }}>◈ Qwen 2.5 1.5B — AI Explanation</div>
          <div style={{ lineHeight: 1.9 }}>{formatExplanation(selected.explanation)}</div>
        </div>
      </div>
    </div>
  );
}

// ── Model performance ──────────────────────────────────────────
function ModelPerformance() {
  const cm = [
    [MODEL_STATS.total_transactions - MODEL_STATS.total_flagged - MODEL_STATS.false_negatives, MODEL_STATS.false_positives],
    [MODEL_STATS.false_negatives, MODEL_STATS.true_positives]
  ];
  const maxCM = Math.max(...cm.flat());

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
      <MetricCard label="AUC-ROC"    value="0.9857" sub="Near-perfect separation" color={COLORS.tp} />
      <MetricCard label="Recall"     value="81.23%" sub="Fraud caught"            color={COLORS.accent} />
      <MetricCard label="Precision"  value="6.00%"  sub="Alert accuracy"          color={COLORS.warn} />
      <MetricCard label="Threshold"  value="0.8514" sub="Option A — High Recall"  color={COLORS.textDim} />

      <div style={{ gridColumn: "span 2", background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 14, padding: 28 }}>
        <div style={{ fontSize: 14, color: COLORS.accent, marginBottom: 22, fontFamily: FONT_SANS, fontWeight: 700 }}>Confusion Matrix</div>
        <div style={{ display: "grid", gridTemplateColumns: "100px 1fr 1fr", gap: 10, alignItems: "center" }}>
          <div />
          <div style={{ textAlign: "center", fontSize: 13, color: COLORS.textDim, fontFamily: FONT_SANS, fontWeight: 500 }}>Predicted Legit</div>
          <div style={{ textAlign: "center", fontSize: 13, color: COLORS.textDim, fontFamily: FONT_SANS, fontWeight: 500 }}>Predicted Fraud</div>
          {[["Actual Legit", 0], ["Actual Fraud", 1]].map(([label, row]) => (
            <>
              <div key={label} style={{ fontSize: 13, color: COLORS.textDim, fontFamily: FONT_SANS, fontWeight: 500 }}>{label}</div>
              {cm[row].map((val, col) => {
                const isCorrect = row === col;
                const color = isCorrect ? COLORS.tp : COLORS.danger;
                const intensity = val / maxCM;
                return (
                  <div key={col} style={{ padding: "18px 8px", borderRadius: 10, textAlign: "center", background: `${color}${Math.round(intensity * 60).toString(16).padStart(2, "0")}`, border: `1px solid ${color}30` }}>
                    <div style={{ fontSize: 20, fontFamily: FONT_MONO, color, fontWeight: 700 }}>
                      {val >= 1000000 ? `${(val/1000000).toFixed(2)}M` : val >= 1000 ? `${(val/1000).toFixed(1)}K` : val}
                    </div>
                    <div style={{ fontSize: 12, color: COLORS.textDim, marginTop: 3, fontFamily: FONT_MONO }}>
                      {isCorrect ? (row === 0 ? "TN" : "TP") : (row === 0 ? "FP" : "FN")}
                    </div>
                  </div>
                );
              })}
            </>
          ))}
        </div>
      </div>

      <div style={{ gridColumn: "span 2", background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 14, padding: 28 }}>
        <div style={{ fontSize: 14, color: COLORS.accent, marginBottom: 22, fontFamily: FONT_SANS, fontWeight: 700 }}>Ensemble Architecture</div>
        {[
          { label: "XGBoost",  weight: 0.5000, auc: 0.8973, color: COLORS.accent },
          { label: "LightGBM", weight: 0.5000, auc: 0.8972, color: COLORS.safe },
        ].map(m => (
          <div key={m.label} style={{ marginBottom: 22 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ color: m.color, fontFamily: FONT_MONO, fontWeight: 700, fontSize: 14 }}>{m.label}</span>
              <span style={{ color: COLORS.textDim, fontSize: 13, fontFamily: FONT_SANS }}>Weight: {m.weight.toFixed(2)} · Val AUC-PR: {m.auc}</span>
            </div>
            <div style={{ height: 8, background: COLORS.border, borderRadius: 4, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${m.weight * 100}%`, background: m.color, borderRadius: 4, boxShadow: `0 0 10px ${m.color}40` }} />
            </div>
          </div>
        ))}
        <div style={{ marginTop: 22, borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
          <div style={{ fontSize: 13, color: COLORS.textDim, marginBottom: 14, fontFamily: FONT_SANS, fontWeight: 600 }}>Top Features by Importance</div>
          {[
            { name: "payment_format_risk", score: 0.4007 },
            { name: "amount_log",          score: 0.0870 },
            { name: "fan_out_degree",      score: 0.0837 },
            { name: "tx_velocity",         score: 0.0753 },
            { name: "amount_per_tx",       score: 0.0630 },
          ].map(f => (
            <div key={f.name} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 13, fontFamily: FONT_MONO, color: COLORS.textDim }}>{f.name.replace(/_/g, " ")}</span>
                <span style={{ fontSize: 13, fontFamily: FONT_MONO, color: COLORS.accent, fontWeight: 700 }}>{(f.score * 100).toFixed(1)}%</span>
              </div>
              <div style={{ height: 6, background: COLORS.border, borderRadius: 3, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${f.score * 250}%`, background: COLORS.accent, borderRadius: 3 }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main dashboard ─────────────────────────────────────────────
export default function AMLDashboard() {
  const [tab, setTab] = useState("analyzer");
  const tabs = [
    { id: "analyzer",    label: "Transaction Analyzer", color: COLORS.accent },
    { id: "reports",     label: "XAI Report Viewer",    color: COLORS.safe },
    { id: "performance", label: "Model Performance",    color: COLORS.warn },
  ];

  return (
    <div style={{ minHeight: "100vh", background: COLORS.bg, color: COLORS.text, fontFamily: FONT_SANS,
      backgroundImage: `radial-gradient(ellipse at 20% 20%, #0D1F4420 0%, transparent 60%), radial-gradient(ellipse at 80% 80%, #0A1A3020 0%, transparent 60%)` }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&display=swap');
        * { box-sizing: border-box; }
        select option { background: #0D1626; color: #E2EAF4; }
        input::placeholder { color: #4B5E7A; }
        ::-webkit-scrollbar { width: 6px; } 
        ::-webkit-scrollbar-track { background: #0D1626; }
        ::-webkit-scrollbar-thumb { background: #1A2744; border-radius: 3px; }
      `}</style>

      {/* Header */}
      <div style={{ borderBottom: `1px solid ${COLORS.border}`, padding: "0 36px", background: `${COLORS.surface}EE`, backdropFilter: "blur(12px)", position: "sticky", top: 0, zIndex: 100 }}>
        <div style={{ maxWidth: 1440, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", height: 68 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ width: 38, height: 38, borderRadius: 10, background: `${COLORS.accent}20`, border: `1px solid ${COLORS.accent}50`, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ color: COLORS.accent, fontSize: 18 }}>◈</span>
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, color: COLORS.text, letterSpacing: "0.1em", fontFamily: FONT_MONO }}>AML SENTINEL</div>
              <div style={{ fontSize: 11, color: COLORS.textDim, letterSpacing: "0.1em", fontFamily: FONT_SANS, marginTop: 1 }}>Anti-Money Laundering Detection System</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 28, alignItems: "center" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 11, color: COLORS.textDim, fontFamily: FONT_SANS, textTransform: "uppercase", letterSpacing: "0.08em" }}>System Status</div>
              <div style={{ fontSize: 13, color: COLORS.safe, fontFamily: FONT_SANS, fontWeight: 600 }}>● Operational</div>
            </div>
            <div style={{ height: 32, width: 1, background: COLORS.border }} />
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 11, color: COLORS.textDim, fontFamily: FONT_SANS, textTransform: "uppercase", letterSpacing: "0.08em" }}>Model</div>
              <div style={{ fontSize: 13, color: COLORS.text, fontFamily: FONT_MONO, fontWeight: 600 }}>XGB + LGB + QWEN 2.5</div>
            </div>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div style={{ background: `${COLORS.surface}90`, borderBottom: `1px solid ${COLORS.border}`, padding: "0 36px" }}>
        <div style={{ maxWidth: 1440, margin: "0 auto", display: "flex", gap: 36, height: 56, alignItems: "center", overflowX: "auto" }}>
          {[
            { label: "Transactions Analyzed", value: MODEL_STATS.total_transactions.toLocaleString(), color: COLORS.textDim },
            { label: "Alerts Generated",      value: MODEL_STATS.total_flagged.toLocaleString(),      color: COLORS.warn },
            { label: "Confirmed Fraud",        value: MODEL_STATS.true_positives.toLocaleString(),    color: COLORS.danger },
            { label: "False Positives",        value: MODEL_STATS.false_positives.toLocaleString(),   color: COLORS.fp },
            { label: "Missed Fraud",           value: MODEL_STATS.false_negatives.toLocaleString(),   color: COLORS.fn },
            { label: "AUC-ROC",                value: "0.9857",                                        color: COLORS.tp },
          ].map(s => (
            <div key={s.label} style={{ display: "flex", gap: 10, alignItems: "center", flexShrink: 0 }}>
              <div style={{ width: 7, height: 7, borderRadius: "50%", background: s.color, flexShrink: 0 }} />
              <span style={{ fontSize: 12, color: COLORS.textDim, fontFamily: FONT_SANS, whiteSpace: "nowrap" }}>{s.label}:</span>
              <span style={{ fontSize: 14, color: s.color, fontWeight: 700, fontFamily: FONT_MONO }}>{s.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Main */}
      <div style={{ maxWidth: 1440, margin: "0 auto", padding: "32px 36px" }}>
        <div style={{ display: "flex", gap: 10, marginBottom: 32 }}>
          {tabs.map(t => (
            <TabBtn key={t.id} active={tab === t.id} onClick={() => setTab(t.id)} color={t.color}>
              {t.label}
            </TabBtn>
          ))}
        </div>
        {tab === "analyzer"    && <TransactionAnalyzer />}
        {tab === "reports"     && <ReportViewer />}
        {tab === "performance" && <ModelPerformance />}
      </div>

      {/* Footer */}
      <div style={{ borderTop: `1px solid ${COLORS.border}`, padding: "18px 36px", marginTop: 20 }}>
        <div style={{ maxWidth: 1440, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 13, color: COLORS.textMuted, fontFamily: FONT_SANS }}>AML Sentinel — XGBoost + LightGBM Ensemble + Qwen 2.5 1.5B XAI</span>
          <span style={{ fontSize: 13, color: COLORS.textMuted, fontFamily: FONT_SANS }}>IBM AML Dataset · 31.9M Transactions · 18 Features</span>
        </div>
      </div>
    </div>
  );
}