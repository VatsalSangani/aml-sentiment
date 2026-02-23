import torch
import math
import re
from threading import Lock

# ── Qwen load-on-demand with thread safety ─────────────────────
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

class XAIService:
    def __init__(self):
        self.tokenizer  = None
        self.model      = None
        self.loaded     = False
        self._lock      = Lock()
        self.threshold  = 0.8514

    def load(self):
        """Load Qwen on first request. Thread-safe."""
        with self._lock:
            if self.loaded:
                return
            from transformers import (AutoModelForCausalLM,
                                      AutoTokenizer,
                                      BitsAndBytesConfig)
            print("Loading Qwen 2.5 1.5B on demand...")
            bnb = BitsAndBytesConfig(
                load_in_4bit              = True,
                bnb_4bit_compute_dtype    = torch.float16,
                bnb_4bit_use_double_quant = True,
                bnb_4bit_quant_type       = "nf4"
            )
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            self.model     = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                quantization_config = bnb,
                device_map          = "auto",
                torch_dtype         = torch.float16
            )
            self.model.eval()
            self.loaded = True
            vram = torch.cuda.memory_allocated() / 1e9
            print(f"Qwen loaded! VRAM used: {vram:.2f} GB")

    def unload(self):
        """Free VRAM when not in use."""
        with self._lock:
            if not self.loaded:
                return
            del self.model
            del self.tokenizer
            self.model     = None
            self.tokenizer = None
            self.loaded    = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("Qwen unloaded - VRAM freed")

    # ── Pre-translate all technical values into plain English ──
    def _translate_features(self, features: dict, shap_drivers: list) -> dict:
        """
        Convert raw ML feature values into human-readable descriptions.
        Qwen never sees feature names, SHAP values, or raw numbers.
        """
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

        if fan <= 3:     fan_desc = f"very low ({fan} recipients — consistent with personal account)"
        elif fan <= 10:  fan_desc = f"normal ({fan} recipients — consistent with small business)"
        elif fan <= 50:  fan_desc = f"elevated ({fan} recipients — warrants review)"
        else:            fan_desc = f"very high ({fan} recipients — strongly associated with smurfing and layering)"

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
                "payment_format_risk" : f"The payment method ({payment_name}) {strength} {direction} the risk assessment",
                "is_in_cycle"         : f"A circular transaction pattern — money sent and returned between the same accounts — {strength} {direction} the risk",
                "bank_risk_score"     : f"The originating bank's history of involvement in suspicious activity {strength} {direction} the risk",
                "is_cross_border"     : f"The fact that funds cross between different banks {strength} {direction} the risk",
                "fan_out_degree"      : f"The number of different recipients this account has sent to ({fan}) {strength} {direction} the risk",
                "tx_velocity"         : f"The account's overall transaction volume {strength} {direction} the risk",
                "amount_log"          : f"The transaction amount {strength} {direction} the risk",
                "amount_per_tx"       : f"The average amount sent per transaction {strength} {direction} the risk",
                "currency_risk_score" : f"The currency used {strength} {direction} the risk due to the regulatory environment of its jurisdiction",
                "is_near_threshold"   : f"The transaction amount being close to the mandatory reporting limit {strength} {direction} the risk",
                "is_high_fan_out"     : f"The unusually large number of recipients {strength} {direction} the risk",
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

    # ── Post-processing validator ──────────────────────────────
    def _validate(self, text: str, features: dict) -> list:
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

    # ── Main explainer ─────────────────────────────────────────
    def explain(self, risk_score: float, features: dict, shap_drivers: list) -> str:
        """Generate plain-English explanation. Loads Qwen if needed."""
        if not self.loaded:
            self.load()

        t = self._translate_features(features, shap_drivers)

        verdict    = "FLAGGED — Suspicious activity detected" if risk_score >= self.threshold else "CLEARED — No suspicious activity detected"
        confidence = "very high" if risk_score >= 0.95 else "high" if risk_score >= 0.85 else "moderate" if risk_score >= 0.70 else "low"

        transaction_summary = f"""What we know about this transaction:
- Payment method  : {t['payment_name']} — {t['payment_desc']}
- Currency        : {features.get('currency', 'Unknown')} — {t['currency_desc']}
- Recipients      : {t['fan_desc']}
- Account activity: {t['vel_desc']}
- Sending bank    : {t['bank_desc']}
- Crosses banks   : {'Yes — funds moving between different institutions' if t['is_cross_border'] else 'No — same institution transfer'}
- Circular pattern: {'Yes — money was sent back to the originating account' if t['is_in_cycle'] else 'No circular pattern detected'}
- Near report limit: {'Yes — amount is in the suspicious $8,000 to $10,000 range' if t['is_near_threshold'] else 'No'}"""

        reasons_text = "\n".join([f"- {s}" for s in t['driver_sentences']])

        system_prompt = """You are a senior AML (Anti-Money Laundering) compliance analyst writing reports for bank investigators.

Your reports must be written in clear, plain English. The reader is a compliance officer, not a data scientist.

STRICT RULES:
1. Never use technical terms: no SHAP, no feature names, no variable names, no model scores
2. Never mention specific dollar amounts — say small, moderate, large, or very large instead
3. Describe risk in plain words: high risk, moderate risk, low risk
4. Only mention cross-bank activity if the facts say Yes under Crosses banks
5. Only mention circular patterns if the facts say Yes under Circular pattern
6. Only mention structuring if the facts say Yes under Near report limit
7. Write like a professional compliance analyst explaining to a senior bank manager
8. Keep each section to 1-2 sentences maximum"""

        user_prompt = f"""OUTCOME: {verdict} ({confidence} confidence)

TRANSACTION FACTS:
{transaction_summary}

WHY THE SYSTEM MADE THIS DECISION:
{reasons_text}

Write the compliance report using EXACTLY this structure:

ALERT STATUS: [One sentence — outcome and confidence level in plain English]

PRIMARY CONCERN: [One sentence — the single most important reason, in plain English, no technical terms]

SUPPORTING EVIDENCE: [Two sentences — explain the two strongest reasons using only the facts above]

INVESTIGATOR NOTE: [One to two sentences — specific actionable next steps for the investigator]"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ]

        text   = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens = 500,
                temperature    = 0.1,
                top_p          = 0.85,
                do_sample      = True,
                pad_token_id   = self.tokenizer.eos_token_id
            )

        generated   = outputs[0][inputs.input_ids.shape[1]:]
        explanation = self.tokenizer.decode(generated, skip_special_tokens=True).strip()

        issues = self._validate(explanation, features)
        if issues:
            explanation += f"\n\nVALIDATION WARNING: {'; '.join(issues)}"

        return explanation

    def get_vram_info(self) -> dict:
        if not torch.cuda.is_available():
            return {"available": False}
        return {
            "available": True,
            "used_gb"  : round(torch.cuda.memory_allocated() / 1e9, 2),
            "total_gb" : round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2)
        }

# ── Singleton ──────────────────────────────────────────────────
xai_service = XAIService()