import json
import os
from pathlib import Path
from typing import Any, Dict

from base import BaseAgent
from llm import call_llm, parse_llm_json

class TrendAgent(BaseAgent):
    """
    Regional Trend Agent: Reads the forecasting cache and uses an LLM
    to generate an autonomous market trend report.
    """

    def __init__(self):
        super().__init__("TrendAgent")
        # Define paths
        self.base_dir = Path(os.path.abspath(__file__)).parent.parent.parent
        self.cache_dir = self.base_dir / "forcasting" / "cache"
        self.outputs_dir = self.base_dir / "backend" / "outputs"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log.info("=" * 60)
        self.log.info("TrendAgent — starting market trend analysis")
        self.log.info("=" * 60)

        # 1. Read Forecast Cache
        forecast_file = self.cache_dir / "dso3_v7_forecast_frontend.json"
        
        if not forecast_file.exists():
            self.log.error(f"Forecast cache not found at {forecast_file}")
            state["trend_agent_status"] = "failed"
            state["trend_agent_error"] = "Cache not found"
            return state

        try:
            with open(forecast_file, "r", encoding="utf-8") as f:
                forecast_data = json.load(f)
            self.log.info(f"Loaded forecast data from {forecast_file.name}")
        except Exception as e:
            self.log.error(f"Failed to load forecast data: {e}")
            state["trend_agent_status"] = "failed"
            state["trend_agent_error"] = str(e)
            return state

        # Extract only the necessary info to not overwhelm the LLM token limit
        payloads = forecast_data.get("payloads", {})
        if not payloads:
            self.log.error("No payloads found in forecast data.")
            state["trend_agent_status"] = "failed"
            state["trend_agent_error"] = "No payloads"
            return state
            
        first_payload = next(iter(payloads.values()))
        regions_info = first_payload.get("regions", [])
        
        # We can also compute global average growth
        growths = [r.get("growth", 0) for r in regions_info]
        overall_growth = round(sum(growths) / len(growths), 1) if growths else 0
        
        # We can get model info from Tunis or average
        model_info = first_payload.get("model", {})
        
        # 2. Build the Prompt for the LLM
        prompt_data = {
            "overall_growth_pct": overall_growth,
            "regions": regions_info,
            "model_reliability": model_info.get("reliability", "Inconnue")
        }

        system_context = (
            "You are the 'Regional Trend Agent', an expert real estate market analyst for LensEstate (Tunisia).\n"
            "Your task is to analyze the following JSON data representing real estate price forecasts for the next 12 months.\n\n"
            f"DATA:\n{json.dumps(prompt_data, indent=2)}\n\n"
            "Based on the data, you must generate a JSON response with exactly three keys:\n"
            "1. 'top_region': the name of the region with the highest growth.\n"
            "2. 'market_summary': A short paragraph (in French) summarizing the overall market trend and identifying which regions are growing or dropping.\n"
            "3. 'investment_recommendation': A short paragraph (in French) giving advice to an investor based on the reliability of the data and the growth.\n\n"
            "Reply ONLY with a valid JSON object."
        )

        self.log.info("Querying LLM for trend analysis...")
        
        # 3. Call LLM
        try:
            raw_response = call_llm(system_context, max_tokens=1024)
            analysis_result = parse_llm_json(raw_response)
            self.log.info("LLM analysis complete.")
            self.log.debug(f"Analysis result: {analysis_result}")
        except Exception as e:
            self.log.error(f"LLM call failed: {e}")
            state["trend_agent_status"] = "failed"
            state["trend_agent_error"] = f"LLM error: {str(e)}"
            return state

        # 4. Save results
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        report_path_json = self.outputs_dir / "regional_trend_report.json"
        report_path_md = self.outputs_dir / "regional_trend_report.md"

        try:
            # Save JSON
            with open(report_path_json, "w", encoding="utf-8") as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)
            
            # Save Markdown (Best format for readability)
            md_content = f"# Rapport de Tendance Régionale (Agent)\n\n"
            md_content += f"**Région la plus prometteuse :** {analysis_result.get('top_region', 'N/A')}\n\n"
            md_content += f"## Résumé du Marché\n{analysis_result.get('market_summary', 'N/A')}\n\n"
            md_content += f"## Recommandation d'Investissement\n{analysis_result.get('investment_recommendation', 'N/A')}\n"
            
            with open(report_path_md, "w", encoding="utf-8") as f:
                f.write(md_content)

            self.log.info(f"Reports successfully saved to {self.outputs_dir}")
        except Exception as e:
            self.log.error(f"Failed to save reports: {e}")

        # Update State
        state = self.update_state(state, "trend_agent_status", "success")
        state = self.update_state(state, "trend_report_path", str(report_path_json))
        state = self.update_state(state, "trend_analysis", analysis_result)
        
        return state

if __name__ == "__main__":
    import logging
    # Quick standalone test
    agent = TrendAgent()
    # Force log output to terminal for standalone run
    logging.getLogger("TrendAgent").setLevel(logging.INFO)
    
    test_state = {}
    print("--- Starting Standalone Run of TrendAgent ---")
    final_state = agent.run(test_state)
    print("\n--- Final State ---")
    print(json.dumps(final_state, indent=2, ensure_ascii=False))
