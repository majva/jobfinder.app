from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.services.cv.skill_catalog import SKILL_CATALOG
from src.infrastructure.di.inject import inject

_SPONSOR_YES = (
    r"visa\s+sponsor",
    r"visa\s+sponsorship",
    r"sponsorship\s+(?:is\s+)?(?:available|provided|offered|supported)",
    r"will\s+sponsor",
    r"we\s+sponsor",
    r"can\s+sponsor",
    r"able\s+to\s+sponsor",
    r"open\s+to\s+sponsorship",
    r"sponsor(?:s|ship)?\s+(?:provided|available|yes|visas?|work\s+permits?)",
    r"work\s+visa\s+(?:support|sponsorship|assistance)",
    r"visa\s+(?:support|assistance|help)",
    r"work\s+permit\s+(?:support|sponsorship|assistance|provided|available)",
    r"relocates?\s+and\s+sponsors?",
    r"visa\s+and\s+relocation",
    r"relocation\s+and\s+visa",
    r"immigration\s+(?:support|assistance|sponsorship)",
    r"international\s+(?:applicants?|candidates?)\s+welcome",
    r"\bh-?1b\b",
    r"\be-?3\b",
    r"\bo-?1\b",
    r"\blmia\b",
    r"eu\s+blue\s+card",
    r"\bblue\s+card\b",
    r"skilled\s+worker\s+visa",
    r"certificate\s+of\s+sponsorship",
    r"sponsor\s+licen[cs]e",
    r"highly\s+skilled\s+migrant",
    r"\bkennismigrant\b",
    r"30\s?%\s+ruling",
    r"tier\s*2\s+visa",
    r"global\s+talent\s+visa",
    r"green\s*card\s+sponsor",
)
_SPONSOR_NO = (
    r"no\s+(?:visa\s+)?sponsorship",
    r"not\s+able\s+to\s+sponsor",
    r"unable\s+to\s+sponsor",
    r"cannot\s+sponsor",
    r"won't\s+sponsor",
    r"will\s+not\s+sponsor",
    r"does\s+not\s+sponsor",
    r"without\s+(?:visa\s+)?sponsorship",
    r"no\s+visa\s+support",
    r"sponsorship\s+is\s+not\s+available",
    r"must\s+be\s+(?:a\s+)?(?:us|u\.s\.|united states|uk|canadian)\s+citizen",
    r"citizens?\s+(?:and|or)\s+permanent\s+residents?\s+only",
    r"must\s+(?:already\s+)?have\s+(?:the\s+)?(?:legal\s+)?right\s+to\s+work",
    r"must\s+already\s+be\s+(?:authorized|authorised)\s+to\s+work",
    r"authorized\s+to\s+work.{0,60}without\s+sponsorship",
    r"authorised\s+to\s+work.{0,60}without\s+sponsorship",
)
_REMOTE = (r"\bremote\b", r"work\s+from\s+home", r"\bwfh\b", r"distributed\s+team")
_HYBRID = (r"\bhybrid\b",)
_ONSITE = (r"\bon-?site\b", r"in[- ]office", r"office[- ]based")
_RELO_OFFERED = (
    r"relocation\s+(?:package|assistance|support|offered|available|bonus|allowance)",
    r"relo(?:cation)?\s+package",
    r"help(?:s|ing)?\s+you\s+relocate",
    r"cover(?:s|ing)?\s+relocation",
    r"moving\s+(?:allowance|expenses|package)",
    r"visa\s+and\s+relocation",
    r"relocation\s+and\s+visa",
)
_RELO_REQUIRED = (
    r"must\s+relocate",
    r"relocation\s+required",
    r"need\s+to\s+be\s+(?:located|based)",
)
_SALARY_RANGE = re.compile(
    r"\$?\s?(\d{2,3})(?:[,\.]?(\d{3}))?\s*[kK]?\s*[-–—to]+\s*\$?\s?(\d{2,3})(?:[,\.]?(\d{3}))?\s*[kK]?",
)
_SALARY_SINGLE = re.compile(r"\$\s?(\d{2,3})(?:[,\.](\d{3}))?\s*[kK]\b")
_YEARS_REQ = re.compile(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", re.I)
_FULL_TIME = re.compile(r"full[-\s]?time", re.I)
_CONTRACT = re.compile(r"\b(?:contract|contractor|freelance)\b", re.I)
_SENIORITY = (
    ("intern", r"\bintern(?:ship)?\b"),
    ("junior", r"\b(?:junior|jr\.?|entry[- ]level)\b"),
    ("mid", r"\b(?:mid[- ]level|intermediate)\b"),
    ("senior", r"\b(?:senior|sr\.?)\b"),
    ("staff", r"\bstaff\b"),
    ("principal", r"\bprincipal\b"),
    ("lead", r"\b(?:tech\s+lead|team\s+lead|lead\s+engineer)\b"),
    ("manager", r"\b(?:engineering\s+manager|manager)\b"),
)


@inject
class JobAnalyzerService:

    def analyze(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        blob = " ".join(
            str(listing.get(key) or "")
            for key in ("title", "company", "location", "description", "workplace_hint")
        )
        lowered = blob.lower()
        salary_text, salary_min, salary_max = self._salary(blob, listing.get("salary_hint"))
        workplace = self._workplace(lowered, listing.get("location") or "", listing.get("workplace_hint"))
        return {
            "workplace_type": workplace,
            "sponsorship": self._sponsorship(lowered),
            "relocation": self._relocation(lowered),
            "salary_text": salary_text,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "employment_type": self._employment_type(lowered),
            "seniority": self._seniority(lowered, listing.get("title") or ""),
            "required_years": self._required_years(listing.get("description") or ""),
            "required_skills": self._required_skills(lowered),
        }

    def _sponsorship(self, lowered: str) -> str:
        if self._any(lowered, _SPONSOR_NO):
            return "no"
        if self._any(lowered, _SPONSOR_YES):
            return "yes"
        return "unknown"

    def _relocation(self, lowered: str) -> str:
        if self._any(lowered, _RELO_OFFERED):
            return "offered"
        if self._any(lowered, _RELO_REQUIRED):
            return "required"
        return "unknown"

    @staticmethod
    def helps_immigration(sponsorship: str, relocation: str = "unknown") -> bool:
        """True only when the listing clearly helps someone move on a work visa.

        Relocation-required is ignored: that just means you must live in the city.
        A moving package without visa language is not enough to immigrate.
        """
        if sponsorship == "no":
            return False
        return sponsorship == "yes"

    def _workplace(self, lowered: str, location: str, hint: Optional[str]) -> str:
        hint_l = (hint or "").lower()
        loc_l = location.lower()
        if "remote" in hint_l or self._any(lowered, _REMOTE) or "remote" in loc_l:
            if self._any(lowered, _HYBRID) or "hybrid" in hint_l:
                return "hybrid"
            return "remote"
        if "hybrid" in hint_l or self._any(lowered, _HYBRID) or "hybrid" in loc_l:
            return "hybrid"
        if "on-site" in hint_l or "onsite" in hint_l or self._any(lowered, _ONSITE):
            return "onsite"
        return "unknown"

    def _salary(
        self, blob: str, hint: Optional[str]
    ) -> Tuple[Optional[str], Optional[int], Optional[int]]:
        text = f"{hint or ''} {blob}"
        match = _SALARY_RANGE.search(text)
        if match:
            low = self._to_salary(match.group(1), match.group(2), "k" in match.group(0).lower() or not match.group(2))
            high = self._to_salary(match.group(3), match.group(4), "k" in match.group(0).lower() or not match.group(4))
            pretty = hint.strip() if hint else f"${low:,} – ${high:,}"
            return pretty, low, high
        single = _SALARY_SINGLE.search(text)
        if single:
            value = self._to_salary(single.group(1), single.group(2), True)
            pretty = hint.strip() if hint else f"${value:,}+"
            return pretty, value, None
        if hint:
            return hint.strip(), None, None
        return None, None, None

    def _employment_type(self, lowered: str) -> Optional[str]:
        if _CONTRACT.search(lowered):
            return "contract"
        if _FULL_TIME.search(lowered):
            return "full-time"
        return None

    def _seniority(self, lowered: str, title: str) -> Optional[str]:
        blob = f"{title} {lowered}".lower()
        for label, pattern in _SENIORITY:
            if re.search(pattern, blob, re.I):
                return label
        return None

    def _required_years(self, description: str) -> Optional[int]:
        years = [int(v) for v in _YEARS_REQ.findall(description or "") if 1 <= int(v) <= 20]
        return max(years) if years else None

    def _required_skills(self, lowered: str) -> List[str]:
        found = []
        for skill in sorted(SKILL_CATALOG, key=len, reverse=True):
            pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
            if re.search(pattern, lowered):
                found.append(skill)
        unique = []
        seen = set()
        for skill in found:
            if skill in seen:
                continue
            seen.add(skill)
            unique.append(skill)
        return unique[:30]

    @staticmethod
    def _any(text: str, patterns: Tuple[str, ...]) -> bool:
        return any(re.search(pattern, text, re.I) for pattern in patterns)

    @staticmethod
    def _to_salary(major: str, minor: Optional[str], treat_as_k: bool) -> int:
        if minor:
            return int(major) * 1000 + int(minor)
        value = int(major)
        if treat_as_k or value < 1000:
            return value * 1000
        return value
