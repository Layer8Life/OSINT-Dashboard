# Free-tier LLM for News enrichment, with an offline fallback

RSS Articles carry no coordinates, and Tech/Science stories often have no place at all, so the collector uses Gemini Flash's free tier to group Articles into Events, assign the Category, resolve the Location (Event Site or Organisation HQ) and write the Summary in one pass. Because a free tier can change or run out without notice, every Refresh must still complete without it: the fallback is offline spaCy entity extraction plus the GeoNames gazetteer and a hand-maintained Organisation HQ list, with lower-quality grouping.

## Considered Options

- **GDELT only**: rejected — already geocoded, but noisy and weak for Tech and Science.
- **Offline extraction only**: kept as the fallback — free and dependable, but misses many locations and cannot write Summaries.
- **Paid LLM**: rejected — goes over the £0 budget.

## Consequences

- The Gemini API key is a GitHub Actions secret that the user creates; the repo never contains it.
- News volume is capped per Category per Refresh, and GDELT is left out of v1, to stay within free-tier quotas.
- Events made by the fallback path may have no Summary; the UI must handle that.
