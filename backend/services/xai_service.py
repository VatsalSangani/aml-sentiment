import os
import re
from threading import Lock
from typing import Any

from openai import OpenAI
from dotenv import load_dotenv

# .env lives at project root (one level above backend/)
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(_ENV_PATH)

# Decision threshold for FLAGGED vs CLEARED. Must match the "threshold" value in
# models/ensemble_weights.json (model_service uses that copy). Derivation and the
# reason for this specific value: see docs/THRESHOLD_DERIVATION.md
XAI_THRESHOLD: float = 0.8514


class XAIService:
    def __init__(self) -> None:
        self.client: OpenAI | None = None
        self.loaded: bool          = False
        self._lock                 = Lock()
        self.threshold: float      = XAI_THRESHOLD

    def load(self) -> None:
        """Initialise OpenAI client. Thread-safe."""
        with self._lock:
            if self.loaded:
                return
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.loaded = True
            print("✅ XAI service ready (GPT-4o-mini)")

    def unload(self) -> None:
        """Release the client reference."""
        with self._lock:
            self.client = None
            self.loaded = False
            print("XAI service unloaded")

    def get_vram_info(self) -> dict[str, Any]:
        return {"available": False}

    def _translate_features(self, features: dict, shap_drivers: list) -> dict:
        """Convert raw ML feature values into human-readable descriptions."""
        pfr = int(features.get("payment_format_risk", 0))
        cr  = int(features.get("currency_risk_score", 3))
        vel = int(features.get("tx_velocity", 0))
        fan = int(features.get("fan_out_degree", 1))

        payment_map = {
            3: ("ACH",                         "high-risk — difficult to reverse, commonly used in layering schemes"),
            2: ("Bitcoin",                     "moderate-risk — pseudonymous digital currency with limited traceability"),
            1: ("Cash / Cheque / Credit Card", "low-risk — standard consumer payment methods"),
            0: ("Wire / Reinvestment",         "low-risk — highly traceable institutional payment method"),
        }
        payment_name, payment_desc = payment_map.get(pfr, ("Unknown", "unknown risk level"))

        currency_risk_map = {
            5: "very high risk — jurisdiction has weak AML oversight",
            4: "high risk — limited regulatory transparency",
            3: "moderate risk — standard international currency",
            2: "low risk — strong regulatory oversight",
            1: "very low risk — highly regulated jurisdiction",
        }
        currency_desc = currency_risk_map.get(cr, "moderate risk")

        if vel < 50:     vel_desc = f"low activity account ({vel} total transactions)"
        elif vel < 500:  vel_desc = f"moderate activity account ({vel} total transactions)"
        elif vel < 5000: vel_desc = f"high activity account ({vel:,} total transactions)"
        else:            vel_desc = f"very high volume account ({vel:,} total transactions — warrants scrutiny)"

        if fan <= 3:    fan_desc = f"very low ({fan} recipients — consistent with personal account)"
        elif fan <= 10: fan_desc = f"normal ({fan} recipients — consistent with small business)"
        elif fan <= 50: fan_desc = f"elevated ({fan} recipients — warrants review)"
        else:           fan_desc = f"very high ({fan} recipients — strongly associated with smurfing and layering)"

        bank_risk = float(features.get("bank_risk_score", 0))
        if bank_risk < 0.1:   bank_desc = "clean record"
        elif bank_risk < 0.2: bank_desc = "minor historical concerns"
        elif bank_risk < 0.3: bank_desc = "moderate laundering history"
        else:                  bank_desc = "significant laundering history — high risk institution"

        driver_sentences = []
        for d in shap_drivers[:3]:
            feat      = d["feature"]
            direction = "increased" if d["shap_val"] > 0 else "reduced"
            strength  = "strongly" if abs(d["shap_val"]) > 1.5 else "moderately" if abs(d["shap_val"]) > 0.5 else "slightly"
            plain_map = {
                "payment_format_risk": f"The payment method ({payment_name}) {strength} {direction} the risk assessment",
                "is_in_cycle"        : f"A circular transaction pattern — money sent and returned between the same accounts — {strength} {direction} the risk",
                "bank_risk_score"    : f"The originating bank's history of involvement in suspicious activity {strength} {direction} the risk",
                "is_cross_border"    : f"The fact that funds cross between different banks {strength} {direction} the risk",
                "fan_out_degree"     : f"The number of different recipients this account has sent to ({fan}) {strength} {direction} the risk",
                "tx_velocity"        : f"The account's overall transaction volume {strength} {direction} the risk",
                "amount_log"         : f"The transaction amount {strength} {direction} the risk",
                "amount_per_tx"      : f"The average amount sent per transaction {strength} {direction} the risk",
                "currency_risk_score": f"The currency used {strength} {direction} the risk due to the regulatory environment of its jurisdiction",
                "is_near_threshold"  : f"The transaction amount being close to the mandatory reporting limit {strength} {direction} the risk",
                "is_high_fan_out"    : f"The unusually large number of recipients {strength} {direction} the risk",
            }
            driver_sentences.append(plain_map.get(feat, f"{feat.replace('_', ' ').title()} {strength} {direction} the risk"))

        return {
            "payment_name"     : payment_name,
            "payment_desc"     : payment_desc,
            "currency_desc"    : currency_desc,
            "vel_desc"         : vel_desc,
            "fan_desc"         : fan_desc,
            "bank_desc"        : bank_desc,
            "driver_sentences" : driver_sentences,
            "is_cross_border"  : features.get("is_cross_border", 0) == 1,
            "is_in_cycle"      : features.get("is_in_cycle", 0) == 1,
            "is_near_threshold": features.get("is_near_threshold", 0) == 1,
        }

    def _validate(self, text: str, features: dict) -> list[str]:
        issues = []
        banned = ["SHAP", "shap_val", "feature importance", "fan_out_degree",
                  "tx_velocity", "payment_format_risk", "is_in_cycle",
                  "is_cross_border", "amount_log", "bank_risk_score"]
        for term in banned:
            if term.lower() in text.lower():
                issues.append(f"technical term leaked: {term}")
        if re.search(r"\$[\d,]{6,}", text):
            issues.append("hallucinated large dollar amount")
        if "per hour" in text.lower() or "per minute" in text.lower():
            issues.append("transaction count described as a rate")
        if features.get("is_near_threshold", 0) == 0 and "structur" in text.lower():
            issues.append("structuring mentioned but amount not near threshold")
        if features.get("is_cross_border", 0) == 0 and "cross-border" in text.lower():
            issues.append("cross-border mentioned but same-bank transaction")
        if features.get("is_in_cycle", 0) == 0 and "circular" in text.lower():
            issues.append("circular pattern mentioned but none detected")
        return issues

    def explain(self, risk_score: float, features: dict, shap_drivers: list) -> str:
        """Generate plain-English compliance explanation via GPT-4o-mini."""
        if not self.loaded:
            self.load()

        t = self._translate_features(features, shap_drivers)

        verdict    = "FLAGGED — Suspicious activity detected" if risk_score >= self.threshold else "CLEARED — No suspicious activity detected"
        confidence = "very high" if risk_score >= 0.95 else "high" if risk_score >= 0.85 else "moderate" if risk_score >= 0.70 else "low"

        transaction_summary = (
            f"What we know about this transaction:\n"
            f"- Payment method  : {t['payment_name']} — {t['payment_desc']}\n"
            f"- Currency        : {features.get('currency', 'Unknown')} — {t['currency_desc']}\n"
            f"- Recipients      : {t['fan_desc']}\n"
            f"- Account activity: {t['vel_desc']}\n"
            f"- Sending bank    : {t['bank_desc']}\n"
            f"- Crosses banks   : {'Yes — funds moving between different institutions' if t['is_cross_border'] else 'No — same institution transfer'}\n"
            f"- Circular pattern: {'Yes — money was sent back to the originating account' if t['is_in_cycle'] else 'No circular pattern detected'}\n"
            f"- Near report limit: {'Yes — amount is in the suspicious $8,000 to $10,000 range' if t['is_near_threshold'] else 'No'}"
        )

        reasons_text = "\n".join(f"- {s}" for s in t["driver_sentences"])

        system_prompt = (
            "You are a senior AML (Anti-Money Laundering) compliance analyst writing reports for bank investigators.\n\n"
            "Your reports must be written in clear, plain English. The reader is a compliance officer, not a data scientist.\n\n"
            "STRICT RULES:\n"
            "1. Never use technical terms: no SHAP, no feature names, no variable names, no model scores\n"
            "2. Never mention specific dollar amounts — say small, moderate, large, or very large instead\n"
            "3. Describe risk in plain words: high risk, moderate risk, low risk\n"
            "4. Only mention cross-bank activity if the facts say Yes under Crosses banks\n"
            "5. Only mention circular patterns if the facts say Yes under Circular pattern\n"
            "6. Only mention structuring if the facts say Yes under Near report limit\n"
            "7. Write like a professional compliance analyst explaining to a senior bank manager\n"
            "8. Keep each section to 1-2 sentences maximum"
        )

        user_prompt = (
            f"OUTCOME: {verdict} ({confidence} confidence)\n\n"
            f"TRANSACTION FACTS:\n{transaction_summary}\n\n"
            f"WHY THE SYSTEM MADE THIS DECISION:\n{reasons_text}\n\n"
            "Write the compliance report using EXACTLY this structure:\n\n"
            "ALERT STATUS: [One sentence — outcome and confidence level in plain English]\n\n"
            "PRIMARY CONCERN: [One sentence — the single most important reason, in plain English, no technical terms]\n\n"
            "SUPPORTING EVIDENCE: [Two sentences — explain the two strongest reasons using only the facts above]\n\n"
            "INVESTIGATOR NOTE: [One to two sentences — specific actionable next steps for the investigator]"
        )

        response = self.client.chat.completions.create(
            model       = "gpt-4o-mini",
            messages    = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens  = 500,
            temperature = 0.1,
            top_p       = 0.85,
        )
        explanation = response.choices[0].message.content.strip()

        issues = self._validate(explanation, features)
        if issues:
            explanation += f"\n\nVALIDATION WARNING: {'; '.join(issues)}"

        return explanation


xai_service = XAIService()
