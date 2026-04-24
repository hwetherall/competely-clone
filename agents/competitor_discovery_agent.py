"""
Competitor discovery agent for Innovera-tuned competitor landscapes.

M4 backend-only implementation:
- expands each framing into neural-search queries
- searches Exa
- extracts top pages with Firecrawl
- asks the discovery model for candidate companies and rationales
- merges, deduplicates, ranks, and persists JSON discovery runs
"""

import asyncio
import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from agents.exa_client import ExaClient
from agents.firecrawl_client import FirecrawlClient
from agents.llm_client import LLMClient
from agents.schemas import CompetitorCandidate, DiscoveryRun, DiscoveryTargetProfile
from config import settings
from config.framings import (
    DEFAULT_FRAMING_SEEDS,
    DISCOVERY_FRAMINGS,
    FRAMING_DEFINITIONS,
    FRAMING_LABELS,
    FRAMING_WEIGHTS,
)
from config.innovera_profile import INNOVERA_PROFILE

logger = logging.getLogger(__name__)

DISCOVERY_DIR = settings.PROJECT_ROOT / "data" / "discovery"
REQUIRED_DISCOVERY_CANDIDATES: list[dict[str, Any]] = [
    {
        "name": "Rocket",
        "canonical_domain": "rocket.new",
        "framings": ["category_sharer", "adjacency"],
        "rationales": {
            "category_sharer": (
                "Required Innovera discovery option: AI-native product/application generation "
                "platform with an adjacent multi-agent workflow shape."
            ),
            "adjacency": (
                "Required Innovera discovery option: could sit near initiative validation, "
                "prototyping, and execution workflows connected to decision intelligence."
            ),
        },
        "evidence_urls": ["https://www.rocket.new/"],
        "confidence": 0.85,
    }
]


class DiscoveryError(Exception):
    """Raised when competitor discovery fails."""


def ensure_discovery_dir() -> None:
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)


def discovery_path(run_id: str) -> Path:
    return DISCOVERY_DIR / f"{run_id}.json"


def save_discovery_run(run: DiscoveryRun) -> None:
    ensure_discovery_dir()
    run.updated_at = datetime.now(timezone.utc)
    with open(discovery_path(run.id), "w", encoding="utf-8") as f:
        json.dump(run.model_dump(mode="json"), f, indent=2, ensure_ascii=False)


def load_discovery_run(run_id: str) -> DiscoveryRun:
    path = discovery_path(run_id)
    if not path.exists():
        raise FileNotFoundError(run_id)
    with open(path, "r", encoding="utf-8") as f:
        return DiscoveryRun.model_validate(json.load(f))


def _extract_result_json(content: str) -> dict:
    """Extract the first JSON object from an LLM response."""
    start_tag = "<result>"
    end_tag = "</result>"
    if start_tag in content:
        start = content.find(start_tag) + len(start_tag)
        end = content.find(end_tag, start)
        block = content[start:end if end != -1 else None].strip()
    else:
        block = content.strip()

    brace_start = block.find("{")
    if brace_start == -1:
        raise ValueError("No JSON object found in discovery response")
    depth = 0
    in_string = False
    escape = False
    quote_char = ""
    end = brace_start
    for i in range(brace_start, len(block)):
        ch = block[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if in_string:
            if ch == quote_char:
                in_string = False
            continue
        if ch in ("'", '"'):
            in_string = True
            quote_char = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    raw = block[brace_start:end]
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)
    return json.loads(raw)


def _domain_from_url(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _normalize_company_name(name: str) -> str:
    cleaned = name.lower().strip()
    cleaned = re.sub(r"[^\w\s.&-]", "", cleaned)
    cleaned = re.sub(
        r"\b(incorporated|inc|llc|ltd|limited|corp|corporation|company|co|plc|gmbh|sa|ag)\b\.?",
        "",
        cleaned,
    )
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _merge_key(name: str, domain: Optional[str]) -> str:
    if domain:
        return f"domain:{domain.lower()}"
    return f"name:{_normalize_company_name(name)}"


def _required_candidates_for_target(target_profile: DiscoveryTargetProfile) -> list[dict[str, Any]]:
    """Return hardcoded discovery options, excluding the target itself."""
    target_norm = _normalize_company_name(target_profile.company_name)
    return [
        candidate.copy()
        for candidate in REQUIRED_DISCOVERY_CANDIDATES
        if _normalize_company_name(str(candidate.get("name", ""))) != target_norm
    ]


def _format_pages_for_prompt(pages: list[Any], max_chars_per_page: int = 1800) -> str:
    chunks = []
    for i, page in enumerate(pages, start=1):
        if not getattr(page, "is_success", False):
            continue
        text = (page.text or "")[:max_chars_per_page]
        chunks.append(
            "\n".join([
                f"[P{i}] {page.title or page.url}",
                f"URL: {page.final_url or page.url}",
                text,
            ])
        )
    return "\n\n".join(chunks) or "No extracted page content available."


def _candidate_from_raw(raw: dict, framing: str, evidence_urls: list[str]) -> dict:
    name = str(raw.get("name", "")).strip()
    domain = raw.get("canonical_domain") or raw.get("domain")
    if domain:
        domain = str(domain).lower().strip()
        domain = domain.removeprefix("https://").removeprefix("http://").removeprefix("www.")
        domain = domain.split("/")[0]
    rationale = str(raw.get("rationale", "")).strip()
    urls = raw.get("evidence_urls") or raw.get("urls") or []
    urls = [str(u) for u in urls if isinstance(u, str)]
    if not urls:
        urls = evidence_urls[:3]
    confidence = raw.get("confidence", 0.6)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.6
    return {
        "name": name,
        "canonical_domain": domain,
        "framings": [framing],
        "rationales": {framing: rationale or f"Matched {FRAMING_LABELS.get(framing, framing)} framing."},
        "evidence_urls": urls,
        "confidence": max(0.0, min(1.0, confidence)),
    }


class CompetitorDiscoveryAgent:
    """Runs framed competitor discovery."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        search_client: Optional[ExaClient] = None,
        page_client: Optional[FirecrawlClient] = None,
        model: Optional[str] = None,
    ):
        self.llm_client = llm_client or LLMClient()
        self.search_client = search_client or ExaClient()
        self.page_client = page_client or FirecrawlClient()
        self.model = model or settings.DISCOVERY_MODEL

    async def discover_direct(self, target_profile: DiscoveryTargetProfile, seed: str) -> list[dict]:
        return await self._discover_framing("direct", target_profile, seed)

    async def discover_problem_sharers(self, target_profile: DiscoveryTargetProfile, seed: str) -> list[dict]:
        return await self._discover_framing("problem_sharer", target_profile, seed)

    async def discover_category_sharers(self, target_profile: DiscoveryTargetProfile, seed: str) -> list[dict]:
        return await self._discover_framing("category_sharer", target_profile, seed)

    async def discover_adjacency(self, target_profile: DiscoveryTargetProfile, seed: str) -> list[dict]:
        return await self._discover_framing("adjacency", target_profile, seed)

    async def run(
        self,
        target_profile: Optional[DiscoveryTargetProfile] = None,
        framing_seeds: Optional[dict[str, str]] = None,
        max_candidates: int = 20,
        run_id: Optional[str] = None,
    ) -> DiscoveryRun:
        target_profile = target_profile or DiscoveryTargetProfile(description=INNOVERA_PROFILE)
        if not target_profile.description:
            target_profile.description = INNOVERA_PROFILE
        seeds = {**DEFAULT_FRAMING_SEEDS, **(framing_seeds or {})}
        max_candidates = max(10, min(30, int(max_candidates or settings.DISCOVERY_MAX_CANDIDATES)))

        run = DiscoveryRun(
            id=run_id or f"discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
            target_profile=target_profile,
            framing_seeds=seeds,
            candidates=[],
            status="running",
            created_at=datetime.now(timezone.utc),
        )
        save_discovery_run(run)

        try:
            framing_tasks = [
                self.discover_direct(target_profile, seeds["direct"]),
                self.discover_problem_sharers(target_profile, seeds["problem_sharer"]),
                self.discover_category_sharers(target_profile, seeds["category_sharer"]),
                self.discover_adjacency(target_profile, seeds["adjacency"]),
            ]
            raw_groups = await asyncio.gather(*framing_tasks, return_exceptions=True)
            raw_candidates: list[dict] = []
            errors = []
            for group in raw_groups:
                if isinstance(group, Exception):
                    errors.append(str(group))
                    logger.warning("Discovery framing failed: %s", group)
                    continue
                raw_candidates.extend(group)
            raw_candidates.extend(_required_candidates_for_target(target_profile))
            if not raw_candidates and errors:
                raise DiscoveryError("; ".join(errors))

            run.candidates = self.merge_and_rank(raw_candidates, max_candidates)
            run.status = "complete"
            save_discovery_run(run)
            return run
        except Exception as e:
            run.status = "failed"
            run.error = str(e)
            save_discovery_run(run)
            raise

    async def _discover_framing(
        self,
        framing: str,
        target_profile: DiscoveryTargetProfile,
        seed: str,
    ) -> list[dict]:
        queries = await self._expand_queries(framing, target_profile, seed)
        search_results = await self.search_client.search_batch(
            queries,
            num_results=8,
            max_concurrent=4,
            company=target_profile.company_name,
            include_text=False,
        )
        urls = []
        for result in search_results:
            if isinstance(result, Exception):
                continue
            for item in result.items:
                if item.url and item.url not in urls:
                    urls.append(item.url)
        urls = urls[:12]
        pages = await self.page_client.fetch_batch(urls[:8], max_concurrent=4, use_cache=True) if urls else []
        return await self._extract_candidates(framing, target_profile, seed, urls, pages)

    async def _expand_queries(
        self,
        framing: str,
        target_profile: DiscoveryTargetProfile,
        seed: str,
    ) -> list[str]:
        prompt = f"""Target profile:
{target_profile.to_prompt()}

Framing: {FRAMING_LABELS.get(framing, framing)}
Definition: {FRAMING_DEFINITIONS[framing]}
Seed guidance: {seed}

Generate 3-5 semantic web search queries to discover candidate competitor companies for this framing.
Prefer specific queries that would surface company pages, landscape posts, funding announcements, and analyst lists.

Output JSON inside <result> tags:
<result>{{"queries": ["query 1", "query 2", "query 3"]}}</result>"""
        content = await self.llm_client.complete_simple(
            prompt=prompt,
            system_prompt="You generate precise search queries for competitor discovery.",
            temperature=0.25,
            max_tokens=900,
            model_override=self.model,
        )
        try:
            data = _extract_result_json(content)
            queries = [str(q).strip() for q in data.get("queries", []) if str(q).strip()]
        except Exception:
            logger.warning("Failed to parse query expansion for %s; using fallback", framing)
            queries = []
        if not queries:
            queries = [
                f"{target_profile.company_name} competitors {seed}",
                f"AI strategy market research competitive intelligence platforms {FRAMING_LABELS.get(framing, framing)}",
                f"companies like {target_profile.company_name} {FRAMING_DEFINITIONS[framing]}",
            ]
        return queries[:5]

    async def _extract_candidates(
        self,
        framing: str,
        target_profile: DiscoveryTargetProfile,
        seed: str,
        urls: list[str],
        pages: list[Any],
    ) -> list[dict]:
        evidence = _format_pages_for_prompt(pages)
        prompt = f"""Target profile:
{target_profile.to_prompt()}

Framing: {FRAMING_LABELS.get(framing, framing)}
Definition: {FRAMING_DEFINITIONS[framing]}
Seed guidance: {seed}

Search result URLs:
{json.dumps(urls[:12], indent=2)}

Extracted evidence:
{evidence}

Extract candidate companies that fit this framing. Return 3-12 candidates.
Do not include the target company itself. Prefer companies with evidence in the URLs/content above.

Output JSON inside <result> tags:
<result>
{{
  "candidates": [
    {{
      "name": "Company",
      "canonical_domain": "company.com",
      "rationale": "One-line why it fits this framing.",
      "evidence_urls": ["https://..."],
      "confidence": 0.7
    }}
  ]
}}
</result>"""
        content = await self.llm_client.complete_simple(
            prompt=prompt,
            system_prompt="You extract competitor candidates as strict JSON. Be concise and evidence-led.",
            temperature=0.2,
            max_tokens=2500,
            model_override=self.model,
        )
        data = _extract_result_json(content)
        candidates = []
        target_norm = _normalize_company_name(target_profile.company_name)
        for raw in data.get("candidates", []):
            if not isinstance(raw, dict):
                continue
            candidate = _candidate_from_raw(raw, framing, urls)
            if not candidate["name"]:
                continue
            if _normalize_company_name(candidate["name"]) == target_norm:
                continue
            candidates.append(candidate)
        return candidates

    def merge_and_rank(self, raw_candidates: list[dict], max_candidates: int = 20) -> list[CompetitorCandidate]:
        grouped: dict[str, dict[str, Any]] = {}
        name_aliases: dict[str, str] = {}
        mention_counts: dict[str, int] = defaultdict(int)
        score_parts: dict[str, float] = defaultdict(float)

        for raw in raw_candidates:
            name = str(raw.get("name", "")).strip()
            if not name:
                continue
            domain = raw.get("canonical_domain")
            urls = list(dict.fromkeys(raw.get("evidence_urls", []) or []))
            if not domain and urls:
                domain = _domain_from_url(urls[0])
            normalized_name = _normalize_company_name(name)
            domain_key = _merge_key(name, domain) if domain else None
            name_key = _merge_key(name, None)
            key = domain_key if domain_key and domain_key in grouped else name_aliases.get(normalized_name)
            if not key:
                key = domain_key or name_key
            name_aliases[normalized_name] = key
            framing = (raw.get("framings") or ["direct"])[0]
            confidence = float(raw.get("confidence", 0.5) or 0.5)
            evidence_quality = min(1.0, 0.4 + 0.15 * len(urls))
            score_parts[key] += confidence * evidence_quality * FRAMING_WEIGHTS.get(framing, 1.0)
            mention_counts[key] += 1

            if key not in grouped:
                grouped[key] = {
                    "name": name,
                    "canonical_domain": domain,
                    "framings": [],
                    "rationales": {},
                    "evidence_urls": [],
                    "confidence_values": [],
                }
            group = grouped[key]
            if len(name) > len(group["name"]):
                group["name"] = name
            if domain and not group["canonical_domain"]:
                group["canonical_domain"] = domain
            for f in raw.get("framings", []):
                if f not in group["framings"]:
                    group["framings"].append(f)
            group["rationales"].update(raw.get("rationales", {}))
            for url in urls:
                if url not in group["evidence_urls"]:
                    group["evidence_urls"].append(url)
            group["confidence_values"].append(confidence)

        ranked = []
        now = datetime.now(timezone.utc)
        for key, group in grouped.items():
            mention_boost = min(1.0, 0.45 + 0.15 * mention_counts[key])
            raw_score = score_parts[key] * mention_boost
            confidence = max(0.0, min(1.0, raw_score))
            ranked.append((raw_score, CompetitorCandidate(
                name=group["name"],
                canonical_domain=group["canonical_domain"],
                framings=group["framings"],
                rationales=group["rationales"],
                evidence_urls=group["evidence_urls"][:8],
                confidence=round(confidence, 2),
                discovered_at=now,
            )))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [candidate for _, candidate in ranked[:max_candidates]]


async def run_discovery(
    target_profile: Optional[DiscoveryTargetProfile] = None,
    framing_seeds: Optional[dict[str, str]] = None,
    max_candidates: int = 20,
    run_id: Optional[str] = None,
) -> DiscoveryRun:
    return await CompetitorDiscoveryAgent().run(
        target_profile=target_profile,
        framing_seeds=framing_seeds,
        max_candidates=max_candidates,
        run_id=run_id,
    )


def run_discovery_sync(
    target_profile: Optional[DiscoveryTargetProfile] = None,
    framing_seeds: Optional[dict[str, str]] = None,
    max_candidates: int = 20,
    run_id: Optional[str] = None,
) -> DiscoveryRun:
    return asyncio.run(run_discovery(target_profile, framing_seeds, max_candidates, run_id))
