import os
import json
import time
import re
import requests
import warnings
from rapidfuzz import process, fuzz
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List

class SECLookupService:
    """Service for looking up companies via SEC.gov API"""

    def __init__(self, user_agent: str = "NGL Financial Analysis (contact@ngl.com)"):
        self.user_agent = user_agent
        self.cik_json_url = "https://www.sec.gov/files/company_tickers.json"
        self.request_delay = 0.25
        self.cache_dir = "cache/sec"
        self.filings_dir = "filings"
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.filings_dir, exist_ok=True)

        self._company_index = None
        self._name_to_cik = None
        self._ticker_to_cik = None
        self._choices = None

    def _fetch_json(self, url: str, save_path: Optional[str] = None) -> Dict[str, Any]:
        """Fetch JSON from URL with proper headers"""
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()

        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        time.sleep(self.request_delay)
        return data

    def _build_company_index(self) -> None:
        """Build searchable index of companies from SEC data"""
        cache_path = os.path.join(self.cache_dir, "company_tickers.json")

        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        else:
            raw = self._fetch_json(self.cik_json_url, save_path=cache_path)

        records = []
        for k, v in raw.items():
            title = v.get("title", "").strip()
            ticker = v.get("ticker", "").strip()
            cik = str(v.get("cik_str", "")).strip()
            records.append({"title": title, "ticker": ticker, "cik": cik})

        self._company_index = records
        self._name_to_cik = {r["title"].lower(): r["cik"] for r in records}
        self._ticker_to_cik = {r["ticker"].upper(): r["cik"] for r in records if r["ticker"]}
        self._choices = [r["title"] for r in records] + [r["ticker"] for r in records if r["ticker"]]

    def _parse_number_from_str(self, s: str) -> Optional[float]:
        """Parse number from string with various formats"""
        if s is None:
            return None

        s = str(s).strip()
        negative = False

        if s.startswith("(") and s.endswith(")"):
            negative = True
            s = s[1:-1]

        mul = 1
        sl = s.lower()
        if "billion" in sl:
            mul = 1_000_000_000
        elif "million" in sl:
            mul = 1_000_000
        elif "thousand" in sl:
            mul = 1_000

        cleaned = re.sub(r"[^\d\.\-,]", "", s).replace(",", "")
        if cleaned == "":
            return None

        try:
            val = float(cleaned)
        except:
            return None

        val *= mul
        if negative:
            val = -val

        return val

    def _get_company_facts(self, cik: str) -> Dict[str, Any]:
        """Get company facts from SEC API"""
        cik_padded = str(int(cik)).zfill(10)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
        cache_path = os.path.join(self.cache_dir, f"companyfacts_{cik_padded}.json")

        return self._fetch_json(url, save_path=cache_path)

    def _extract_key_financials(self, company_facts_json: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key financial metrics from company facts"""
        target_keywords = {
            "TotalAssets": ["Assets", "AssetsTotal"],
            "TotalLiabilities": ["Liabilities", "LiabilitiesAndStockholdersEquity", "LiabilitiesTotal"],
            "Revenues": ["Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"],
            "NetIncomeLoss": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
            "CashAndCashEquivalents": ["CashAndCashEquivalentsAtCarryingValue", "CashAndCashEquivalents"]
        }

        found = {}
        facts = company_facts_json.get("facts", {})

        for ns, ns_obj in facts.items():
            for tag, tag_obj in ns_obj.items():
                lt = tag.lower()

                for k, variants in target_keywords.items():
                    for var in variants:
                        if var.lower() in lt:
                            units = tag_obj.get("units", {})
                            chosen_unit = None

                            if "USD" in units:
                                chosen_unit = "USD"
                            elif units:
                                chosen_unit = list(units.keys())[0]

                            if not chosen_unit:
                                continue

                            entries = units.get(chosen_unit, [])
                            if not entries:
                                continue

                            entries_sorted = sorted(entries, key=lambda e: e.get("end") or "", reverse=True)

                            for entry in entries_sorted:
                                num = self._numeric_from_entry(entry)
                                if num is not None:
                                    found[k] = {
                                        "value": num,
                                        "unit": chosen_unit,
                                        "end": entry.get("end")
                                    }
                                    break

        return found

    def _numeric_from_entry(self, entry: Dict[str, Any]) -> Optional[float]:
        """Extract numeric value from entry"""
        for k in ("v", "val", "value", "amount"):
            if k in entry:
                return self._parse_number_from_str(entry.get(k))

        for k, v in entry.items():
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str) and re.search(r"[\d\.,\(\)]", v):
                nn = self._parse_number_from_str(v)
                if nn is not None:
                    return nn

        return None

    def lookup_company(self, company_name: str, threshold: int = 85) -> Dict[str, Any]:
        """
        Look up company by name/ticker and return financial data
        
        Returns:
        {
            "success": bool,
            "data": {
                "company_name": str,
                "ticker": str,
                "cik": str,
                "financials": dict,
                "match_score": int
            } or None,
            "error": str or None,
            "suggestions": list of suggested matches
        }
        """
        try:
            if self._company_index is None:
                self._build_company_index()

            query = company_name.strip()

            if query.upper() in self._ticker_to_cik:
                cik = self._ticker_to_cik[query.upper()]
                return self._get_company_data(cik, query.upper(), 100)

            if query.lower() in self._name_to_cik:
                cik = self._name_to_cik[query.lower()]
                return self._get_company_data(cik, query, 100)

            wratio_matches = process.extract(query, self._choices, scorer=fuzz.WRatio, limit=10)
            partial_matches = process.extract(query, self._choices, scorer=fuzz.partial_ratio, limit=10)
            token_matches = process.extract(query, self._choices, scorer=fuzz.token_sort_ratio, limit=10)

            all_matches = {}
            for match_list in [wratio_matches, partial_matches, token_matches]:
                for name, score, idx in match_list:
                    if name in all_matches:
                        all_matches[name] = max(all_matches[name], score)
                    else:
                        all_matches[name] = score

            matches = [(name, score, 0) for name, score in sorted(all_matches.items(), key=lambda x: x[1], reverse=True)][:5]

            if not matches:
                return {
                    "success": False,
                    "error": "No companies found matching your search",
                    "suggestions": []
                }

            best_match, best_score, _ = matches[0]

            if len(query) >= 4:
                try:
                    from .gemini_service import GeminiFinancialExtractor
                    gemini = GeminiFinancialExtractor()

                    available_companies = [r["title"] for r in self._company_index]
                    gemini_result = gemini.resolve_company_name(query, available_companies)

                    if gemini_result["success"] and gemini_result["suggestions"]:
                        top_suggestion = gemini_result["suggestions"][0]
                        if top_suggestion["confidence"] >= 85:
                            suggested_name = top_suggestion["company_name"]
                            if suggested_name.lower() in self._name_to_cik:
                                cik = self._name_to_cik[suggested_name.lower()]
                                return self._get_company_data(cik, suggested_name, top_suggestion["confidence"])

                        gemini_suggestions = []
                        for suggestion in gemini_result["suggestions"]:
                            gemini_suggestions.append({
                                "name": suggestion["company_name"],
                                "score": suggestion["confidence"],
                                "reason": suggestion.get("reason", "")
                            })

                        return {
                            "success": False,
                            "error": "Multiple possible matches found (AI-assisted)",
                            "suggestions": gemini_suggestions
                        }
                except Exception as e:
                    print(f"Gemini resolution failed: {e}")

            if best_score >= threshold:
                if best_match.upper() in self._ticker_to_cik:
                    cik = self._ticker_to_cik[best_match.upper()]
                else:
                    cik = self._name_to_cik.get(best_match.lower())

                if cik:
                    return self._get_company_data(cik, best_match, best_score)

            suggestion_matches = [(name, score) for name, score, _ in matches if score >= 40]
            suggestions = [{"name": match[0], "score": match[1]} for match in suggestion_matches]

            if not suggestions:
                return {
                    "success": False,
                    "error": "No companies found matching your search",
                    "suggestions": []
                }

            return {
                "success": False,
                "error": "Multiple possible matches found",
                "suggestions": suggestions
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Lookup failed: {str(e)}",
                "suggestions": []
            }

    def _get_company_data(self, cik: str, matched_name: str, score: int) -> Dict[str, Any]:
        """Get complete company data for a CIK"""
        try:
            company_facts = self._get_company_facts(cik)

            financials = self._extract_key_financials(company_facts)

            company_info = next(
                (r for r in self._company_index if r["cik"] == cik),
                {"title": matched_name, "ticker": "", "cik": cik}
            )

            def get_financial_value(key):
                return financials.get(key, {}).get("value")

            formatted_financials = {
                "revenue": get_financial_value("Revenues"),
                "net_income": get_financial_value("NetIncomeLoss"),
                "total_assets": get_financial_value("TotalAssets"),
                "total_liabilities": get_financial_value("TotalLiabilities"),
                "cash_and_equivalents": get_financial_value("CashAndCashEquivalents"),
                "raw_data": financials
            }

            return {
                "success": True,
                "data": {
                    "company_name": company_info["title"],
                    "ticker": company_info["ticker"],
                    "cik": cik,
                    "financials": formatted_financials,
                    "match_score": score,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "error": None,
                "suggestions": []
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to retrieve company data: {str(e)}",
                "suggestions": []
            }

sec_lookup_service = SECLookupService()
