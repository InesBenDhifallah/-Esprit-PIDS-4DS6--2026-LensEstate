# ─────────────────────────────────────────────────────────────────────────────
# CELL 116 — Schema constants + StandardizationAgent  (full replacement)
# ─────────────────────────────────────────────────────────────────────────────

# ── Shared schema (unchanged) ─────────────────────────────────────────────────
LISTINGS_SCHEMA = {
    "listing_id":(object,None),"listing_url":(object,None),"source":(object,None),
    "title":(object,None),"property_type":(object,None),"transaction_type":(object,None),
    "price":(float,np.nan),"currency":(object,"TND"),"surface_m2":(object,None),
    "rooms":(float,np.nan),"total_rooms":(float,np.nan),"bedrooms":(object,None),
    "bathrooms":(float,np.nan),"floor":(float,np.nan),"total_floors":(float,np.nan),
    "country":(object,"Tunisia"),"governorate":(object,None),"city":(object,None),
    "description":(object,None),"image_count":(int,0),"image_urls":(object,None),
    "date_posted":(object,None),"last_updated":(float,np.nan),"agency_name":(object,None),
    "seller_type":(object,None),"scrape_timestamp":(object,None),
    "has_elevator":(object,None),"has_basement":(bool,False),"has_heating":(object,None),
    "has_air_conditioning":(object,None),"has_garden":(bool,False),
    "has_furniture":(bool,False),"has_parking":(object,None),"has_pool":(bool,False),
    "has_security":(object,None),"has_standing":(bool,False),
    "has_terrace":(bool,False),"has_sea_view":(bool,False),
}
TX_MAP = {"Sale":"Sale","sale":"Sale","À Vendre":"Sale","Vente":"Sale",
          "rent":"Rent","Rent":"Rent","À Louer":"Rent","Location":"Rent"}
MUBAWAB_RENAME = {
    "has_ascenseur":"has_elevator","has_cave":"has_basement",
    "has_chauffage":"has_heating","has_climatisation":"has_air_conditioning",
    "has_jardin":"has_garden","has_meuble":"has_furniture",
    "has_piscine":"has_pool","has_gardiennage":"has_security",
    "has_terrasse":"has_terrace","has_vue_mer":"has_sea_view",
}
TAYARA_RENAME = {
    "surface":"surface_m2","criteria_ascenseur":"has_elevator",
    "criteria_climatisation":"has_air_conditioning","criteria_chauffage":"has_heating",
    "criteria_parking":"has_parking","criteria_gardiennage":"has_security",
}

def _align(df: pd.DataFrame) -> pd.DataFrame:
    for col, (dtype, default) in LISTINGS_SCHEMA.items():
        if col not in df.columns:
            df[col] = (False if dtype == bool
                       else np.nan if dtype == float
                       else 0 if dtype == int
                       else default)
    return df[
        [c for c in LISTINGS_SCHEMA] +
        [c for c in df.columns if c not in LISTINGS_SCHEMA]
    ]


class StandardizationAgent(BaseAgent):
    """
    Aligns raw CSVs from each scraper to the shared LISTINGS_SCHEMA.

    New in Phase 2: LLM schema repair.
    When a file's columns don't match known patterns, the LLM inspects
    a sample and proposes the correct rename mapping — so the pipeline
    adapts to minor scraper schema drift without manual code changes.
    """

    def __init__(self):
        super().__init__("StandardizationAgent")

    # ── Public entry point ────────────────────────────────────────────────────
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log.info("=" * 60)
        self.log.info("StandardizationAgent — starting")
        self.log.info("=" * 60)
        self.memory.clear()

        paths = state.get("listings_raw_paths", [])
        self.log.info(f"Input paths ({len(paths)}):")
        for p in paths:
            self.log.info(f"  → {p}")

        dfs = []
        for path in paths:
            self.log.info(f"\nStandardizing: {path}")
            df = self._standardize(path)
            if df is not None and not df.empty:
                dfs.append(df)
                source = df["source"].iloc[0] if "source" in df.columns else "?"
                self.log.info(f"  ✅ {len(df):,} rows | source={source}")
            else:
                self.log.warning("  ⚠️  Empty result — skipping")

        if not dfs:
            self.log.error("No data to merge — all sources failed standardization")
            return self.update_state(state, "standardization_status", "failed")

        merged = pd.concat(dfs, ignore_index=True)
        if "id" in merged.columns:
            merged = merged.drop(columns=["id"])
        merged.insert(0, "id", range(1, len(merged) + 1))

        out = "Data/raw_listings/merged_listings.csv"
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(out, index=False)

        src_dist = merged["source"].value_counts().to_dict() if "source" in merged.columns else {}
        self.log.info(f"\n{'─'*50}")
        self.log.info(f"Merged: {len(merged):,} rows, {merged.shape[1]} cols → {out}")
        for src, cnt in src_dist.items():
            self.log.info(f"  {src:<25} {cnt:>7,}")
        self.log.info(f"{'─'*50}")

        self.memory.remember("quality", {"rows": len(merged), "cols": merged.shape[1], "sources": src_dist})
        state = self.update_state(state, "merged_listings_path",   out)
        state = self.update_state(state, "standardization_status", "success")
        state = self.update_state(state, "standardization_report", {"rows": len(merged), "sources": src_dist})
        return state

    # ── Per-file standardization ───────────────────────────────────────────────
    def _standardize(self, path: str) -> Optional[pd.DataFrame]:
        try:
            df = pd.read_csv(path, low_memory=False)
            pl = path.lower()
            self.log.debug(f"  Raw shape: {df.shape} | cols: {df.columns.tolist()[:8]}...")

            if "mubawab" in pl:
                df["source"]           = "mubawab"
                df["transaction_type"] = "Sale"
                drop = ["price_type", "district", "language", "characteristics", "has_bathrooms"]
                df = df.drop(columns=[c for c in drop if c in df.columns])
                df = df.rename(columns={k: v for k, v in MUBAWAB_RENAME.items() if k in df.columns})

            elif "tayara" in pl:
                df["source"]  = "tayara"
                df["country"] = "Tunisia"
                drop = ["price_raw", "location_raw", "category",
                        "criteria_celliers", "criteria_parking_sous_sol"]
                df = df.drop(columns=[c for c in drop if c in df.columns])
                df = df.rename(columns={k: v for k, v in TAYARA_RENAME.items() if k in df.columns})
                if "has_bathrooms" in df.columns:
                    df["bathrooms"] = df["has_bathrooms"]
                    df = df.drop(columns=["has_bathrooms"])

            elif "tunisie" in pl:
                df["source"] = "tunisie_annonce"
                if "type_transaction" in df.columns:
                    df["transaction_type"] = df["type_transaction"].map(TX_MAP).fillna(df["type_transaction"])
                    df = df.drop(columns=["type_transaction"])
                if "region" in df.columns:
                    split = df["region"].str.split(" - ", n=1, expand=True)
                    df["governorate"] = split[0] if 0 in split.columns else None
                    df["city"]        = split[1] if 1 in split.columns else None
                    df = df.drop(columns=["region"])

            else:
                # ── Unknown source: ask LLM to propose column mapping ─────
                self.log.info("  Unknown source pattern — invoking LLM schema repair")
                df = self._llm_schema_repair(path, df)

            return _align(df)

        except Exception as e:
            self.log.error(f"Standardization error [{path}]: {e}")
            return None

    # ── LLM schema repair (new) ───────────────────────────────────────────────
    def _llm_schema_repair(self, path: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Called when a CSV doesn't match any known scraper pattern.
        The LLM sees the column names + 3 sample rows and proposes:
          1. A rename mapping  (raw_col → schema_col)
          2. A source label
          3. Any columns to drop

        This lets the pipeline adapt to new scrapers or renamed columns
        without requiring a code change.
        """
        sample_rows = df.head(3).to_dict(orient="records")
        known_cols  = list(LISTINGS_SCHEMA.keys())

        prompt = (
            f"A new real estate CSV from Tunisia has been loaded with unknown column names.\n"
            f"File: {path}\n\n"
            f"Raw columns: {df.columns.tolist()}\n\n"
            f"Sample rows (first 3):\n{json.dumps(sample_rows, ensure_ascii=False, default=str)}\n\n"
            f"Target schema columns: {known_cols}\n\n"
            "Map the raw columns to the target schema where possible.\n"
            "Return ONLY this JSON:\n"
            "{\n"
            '  "thought": "explain your mapping reasoning",\n'
            '  "source_label": "name for this scraper (e.g. new_source)",\n'
            '  "rename": {"raw_col": "schema_col", ...},\n'
            '  "drop": ["col_to_drop", ...]\n'
            "}"
        )

        result = self.decide(prompt)

        thought      = result.get("thought", "")
        source_label = result.get("source_label", "unknown_source")
        rename_map   = result.get("rename", {})
        drop_cols    = result.get("drop", [])

        self.log.info(f"  LLM schema repair thought: {thought[:200]}")
        self.log.info(f"  source_label : {source_label}")
        self.log.info(f"  rename map   : {rename_map}")
        self.log.info(f"  drop cols    : {drop_cols}")

        # Persist the inferred mapping for human review
        self.memory.remember("schema_repairs", {
            "path":         path,
            "source_label": source_label,
            "rename":       rename_map,
            "drop":         drop_cols,
            "thought":      thought,
        })

        df = df.drop(columns=[c for c in drop_cols if c in df.columns])
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        df["source"] = source_label
        return df

print("✅ StandardizationAgent defined (LLM schema repair)")
