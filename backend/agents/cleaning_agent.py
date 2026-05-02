import re
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from base import BaseAgent
from standardize_agent import TX_MAP

# ── Geography constants ───────────────────────────────────────────────────────

CITY_TO_GOV = {
    "Tunis":"Tunis","La Marsa":"Tunis","Gammarth":"Tunis","Ain Zaghouan":"Tunis",
    "La Soukra":"Tunis","Ennasr":"Tunis","El Kram":"Tunis","El Ghazela":"Tunis",
    "Ariana":"Ariana","Raoued":"Ariana","Mnihla":"Ariana","Ettadhamen":"Ariana",
    "Ben Arous":"Ben Arous","Rades":"Ben Arous","Boumhel":"Ben Arous",
    "El Mourouj":"Ben Arous","Mégrine":"Ben Arous","Hammam Lif":"Ben Arous",
    "Manouba":"Manouba","Oued Ellil":"Manouba","Douar Hicher":"Manouba",
    "Nabeul":"Nabeul","Hammamet":"Nabeul","Kelibia":"Nabeul","Korba":"Nabeul",
    "Sousse":"Sousse","Hammam Sousse":"Sousse","Sahloul":"Sousse","Akouda":"Sousse",
    "Monastir":"Monastir","Sfax":"Sfax","Gremda":"Sfax","Sakiet Ezzit":"Sfax",
    "Mahdia":"Mahdia","Kairouan":"Kairouan","Bizerte":"Bizerte",
    "Djerba":"Médenine","Zarzis":"Médenine","Midoun":"Médenine",
    "Gabès":"Gabès","Gafsa":"Gafsa","Tozeur":"Tozeur","Tataouine":"Tataouine",
}

PT_MAP = {
    "Appartement":"Apartment","appartement":"Apartment",
    "Maison":"House","maison":"House",
    "Terrain":"Land","terrain":"Land",
    "others":"Other","Autre":"Other",
    "Local Commercial":"Commercial","Commerce":"Commercial",
    "Villa":"Villa","villa":"Villa",
    "Bureau":"Office","bureau":"Office",
    "Immeuble":"Building","Ferme":"Farm",
    "Duplex":"Duplex","Studio":"Studio",
}

SORTED_CITIES = sorted(CITY_TO_GOV.keys(), key=len, reverse=True)


# ── CleaningAgent ─────────────────────────────────────────────────────────────

class CleaningAgent(BaseAgent):
    """
    Cleans and prepares the merged listings for modelling.
    LLM anomaly detection runs in batches, flags suspicious listings.
    """

    DROP_COLS = ["total_floors", "last_updated", "floor",
                 "scrape_timestamp", "date_posted", "agency_name"]

    SAMPLE_SIZE   = 40
    MAX_BATCHES   = 3
    SUSPICIOUS_PROMPT = (
        "You are a data quality agent reviewing real estate listings from Tunisia.\n"
        "Identify listings that are SUSPICIOUS — meaning any of:\n"
        "  - Placeholder or test data (description says 'test', 'lorem ipsum', etc.)\n"
        "  - Price is clearly wrong: < 5,000 TND for any property, or > 50,000,000 TND\n"
        "  - Surface is impossible: < 10 m² or > 50,000 m²\n"
        "  - Description is in a language unrelated to Tunisian real estate\n"
        "  - Description is copy-pasted noise or irrelevant content\n\n"
        "For each suspicious listing give a brief reason.\n\n"
        "Return ONLY this JSON:\n"
        "{\n"
        '  "thought": "overall observations about this batch",\n'
        '  "flagged": [\n'
        '    {"id": 123, "reason": "price=1 TND, clearly placeholder"},\n'
        '    ...\n'
        '  ]\n'
        "}\n"
        "Empty list if nothing suspicious.\n\n"
        "LISTINGS:\n"
    )

    def __init__(self):
        super().__init__("CleaningAgent")

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log.info("=" * 60)
        self.log.info("CleaningAgent — starting")
        self.log.info("=" * 60)
        self.memory.clear()

        path = state.get("merged_listings_path", "")
        if not path or not Path(path).exists():
            self.log.error(f"Merged listings not found: {path}")
            return self.update_state(state, "cleaning_status", "failed")

        df = pd.read_csv(path, low_memory=False)
        self.log.info(f"Loaded: {len(df):,} rows × {df.shape[1]} cols")
        initial = len(df)

        df = self._pipeline(df)

        self.log.info("\nRunning LLM anomaly detection...")
        flagged     = self._flag_suspicious(df)
        flagged_map = {item["id"]: item["reason"] for item in flagged}

        df["llm_suspicious"]        = df["id"].isin(flagged_map.keys()) if "id" in df.columns else False
        df["llm_suspicious_reason"] = df["id"].map(flagged_map).fillna("") if "id" in df.columns else ""

        n_flagged = df["llm_suspicious"].sum()
        self.log.info(f"LLM flagged {n_flagged} suspicious listings (tagged, not dropped)")
        if flagged:
            for item in flagged[:5]:
                self.log.info(f"  ID {item['id']}: {item['reason']}")
            if len(flagged) > 5:
                self.log.info(f"  ... and {len(flagged)-5} more")

        self.memory.remember("suspicious_flags", {
            "total_flagged": int(n_flagged),
            "flagged_ids":   [int(f["id"]) for f in flagged],
            "details":       flagged,
        })

        out = "Data/raw_listings/merged_listings_model_ready.csv"
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)

        null_rates = {
            col: float(round(df[col].isna().mean(), 3))
            for col in ["price", "surface_m2", "governorate", "property_type"]
            if col in df.columns
        }
        report = {
            "initial":            initial,
            "final":              len(df),
            "removed":            initial - len(df),
            "suspicious":         int(n_flagged),
            "null_rate":          null_rates,
            "duplicates_removed": initial - len(df),
        }

        self.log.info(f"\n{'─'*50}")
        self.log.info(f"Cleaning summary:")
        self.log.info(f"  Initial rows : {initial:,}")
        self.log.info(f"  Final rows   : {len(df):,}")
        self.log.info(f"  Removed      : {initial-len(df):,}")
        self.log.info(f"  Suspicious   : {n_flagged}")
        self.log.info(f"  Null rates   : {null_rates}")
        self.log.info(f"  Output       : {out}")
        self.log.info(f"{'─'*50}")

        self.memory.remember("quality", report)
        state = self.update_state(state, "model_ready_path", out)
        state = self.update_state(state, "cleaning_status",  "success")
        state = self.update_state(state, "cleaning_report",  report)
        state = self.update_state(state, "final_row_count",  len(df))
        return state

    def _pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        steps = []
        def _step(name, n):
            steps.append((name, n))
            self.log.info(f"  [{name}] {n:,} rows")

        df["source"]           = df["source"].str.lower().str.strip()
        df["transaction_type"] = df["transaction_type"].map(TX_MAP).fillna(df["transaction_type"])
        df["property_type"]    = df["property_type"].map(PT_MAP).fillna(df["property_type"])
        self.log.info("\nCleaning pipeline:")
        _step("normalize", len(df))

        def fill_gov(row):
            if pd.isna(row.get("governorate")) and pd.notna(row.get("city")):
                return CITY_TO_GOV.get(str(row["city"]).strip(), row.get("governorate"))
            return row.get("governorate")
        df["governorate"] = df.apply(fill_gov, axis=1)

        for idx, row in df[df["governorate"].isna() & df["city"].isna()].iterrows():
            text = f"{row.get('title','')} {row.get('description','')}".lower()
            for city in SORTED_CITIES:
                if re.search(r'\b' + re.escape(city.lower()) + r'\b', text):
                    df.at[idx, "city"]        = city
                    df.at[idx, "governorate"] = CITY_TO_GOV[city]
                    break
        _step("gov_recovery", len(df))

        df = df[df["transaction_type"] == "Sale"].reset_index(drop=True)
        _step("remove_rent", len(df))

        df = df.drop_duplicates(subset=["description"], keep="first").reset_index(drop=True)
        _step("dedup_description", len(df))

        df = df.drop(columns=[c for c in self.DROP_COLS if c in df.columns])
        df = df[df["description"].notna()].reset_index(drop=True)
        _step("drop_null_desc", len(df))

        df["description_word_count"] = df["description"].str.split().str.len()
        df["has_images"]  = (df["image_count"] > 0) if "image_count" in df.columns else False
        df["image_urls"]  = df["image_urls"].fillna("") if "image_urls" in df.columns else ""

        for col in ["has_elevator","has_heating","has_air_conditioning","has_parking","has_security"]:
            if col in df.columns:
                df[col] = df[col].fillna(False).map(
                    lambda x: False if str(x).lower() in ("false","0","nan","") else bool(x))

        def enc(v):
            if isinstance(v, str):
                v = v.lower()
                if any(k in v for k in ["agence","agency","pro"]): return 1
                if any(k in v for k in ["particulier","individual"]): return 0
            return -1
        df["is_agency"] = df["seller_type"].apply(enc) if "seller_type" in df.columns else -1

        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["price"] = df["price"].where(df["price"] > 0)
        df["is_price_imputed"] = df["price"].isna()
        m_tg = df.groupby(["property_type","governorate"])["price"].median()
        m_t  = df.groupby("property_type")["price"].median()
        gm   = df["price"].median()
        def ip(r):
            if pd.notna(r["price"]): return r["price"]
            k = (r["property_type"], r["governorate"])
            if k in m_tg.index and pd.notna(m_tg[k]): return m_tg[k]
            if r["property_type"] in m_t.index and pd.notna(m_t[r["property_type"]]): return m_t[r["property_type"]]
            return gm
        df["price"] = df.apply(ip, axis=1)
        _step("price_imputed", int(df["is_price_imputed"].sum()))

        df["surface_m2"] = pd.to_numeric(df["surface_m2"], errors="coerce")
        df["surface_m2"] = df["surface_m2"].where(df["surface_m2"] > 0)
        df["has_surface"] = df["surface_m2"].notna()
        sm_t = df.groupby("property_type")["surface_m2"].median()
        gsm  = df["surface_m2"].median()
        df["surface_m2"] = df.apply(
            lambda r: r["surface_m2"] if pd.notna(r["surface_m2"])
                      else sm_t.get(r["property_type"], gsm), axis=1)

        for col in ["rooms","bathrooms","bedrooms"]:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce")
        df["has_rooms_info"]     = df["rooms"].notna()     if "rooms"     in df.columns else False
        df["has_bathrooms_info"] = df["bathrooms"].notna() if "bathrooms" in df.columns else False
        df["has_bedrooms_info"]  = df["bedrooms"].notna()  if "bedrooms"  in df.columns else False
        if "total_rooms" in df.columns: df = df.drop(columns=["total_rooms"])

        df = df[df["governorate"].notna()].reset_index(drop=True)
        _step("drop_null_gov", len(df))

        return df

    def _flag_suspicious(self, df: pd.DataFrame) -> List[Dict]:
        if "id" not in df.columns or len(df) == 0:
            return []

        all_flagged: List[Dict] = []
        sample_df = df[["id","title","price","surface_m2","property_type",
                         "governorate","source","description"]] \
                    .dropna(subset=["description"]) \
                    .sample(min(self.SAMPLE_SIZE * self.MAX_BATCHES, len(df)), random_state=42)

        batches = [
            sample_df.iloc[i : i + self.SAMPLE_SIZE]
            for i in range(0, len(sample_df), self.SAMPLE_SIZE)
        ]

        for batch_num, batch in enumerate(batches[:self.MAX_BATCHES], 1):
            self.log.info(f"  Anomaly detection batch {batch_num}/{min(len(batches), self.MAX_BATCHES)} ({len(batch)} rows)")

            lines = [
                f"ID={r['id']} | {r.get('property_type','?')} | {r.get('governorate','?')} | "
                f"Source={r.get('source','?')} | "
                f"Price={r.get('price','?')} TND | Surface={r.get('surface_m2','?')} m² | "
                f"Desc: {str(r.get('description',''))[:200]}"
                for _, r in batch.iterrows()
            ]

            prompt = self.SUSPICIOUS_PROMPT + "\n".join(lines)

            try:
                result  = self.decide(prompt)
                thought = result.get("thought", "")
                flagged = result.get("flagged", [])

                self.log.info(f"  LLM thought: {thought[:180]}")
                self.log.info(f"  Flagged in batch: {len(flagged)}")

                for item in flagged:
                    try:
                        all_flagged.append({
                            "id":     int(item["id"]),
                            "reason": str(item.get("reason", "no reason given")),
                        })
                    except (KeyError, ValueError, TypeError):
                        continue

            except Exception as e:
                self.log.warning(f"  LLM anomaly detection batch {batch_num} failed: {e}")
                continue

        seen = set()
        deduped = []
        for item in all_flagged:
            if item["id"] not in seen:
                seen.add(item["id"])
                deduped.append(item)

        self.log.debug(f"Total suspicious flags: {len(deduped)}")
        return deduped
