#!/usr/bin/env python3
"""Collect and aggregate public repository clone traffic for salianDheeraj."""
from __future__ import annotations
import datetime as dt
import json, os, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

OWNERS = [o.strip() for o in os.environ.get("GH_OWNERS", "salianDheeraj,GitOnBoard").split(",") if o.strip()]
TOKEN = os.environ.get("TRAFFIC_TOKEN") or os.environ.get("GH_TOKEN")
ORG_TOKEN = os.environ.get("TRAFFIC_TOKEN_ORG") or TOKEN
API = "https://api.github.com"
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/repo-traffic.json"
SVG_PATH = ROOT / "assets/repo-traffic.svg"
README_PATH = ROOT / "README.md"
START = "<!-- REPO-TRAFFIC:START -->"
END = "<!-- REPO-TRAFFIC:END -->"

def api_get(url, token=None):
    use_tok = token or TOKEN
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {use_tok}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "salianDheeraj-repo-traffic-dashboard",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def public_repos():
    out = []
    for owner in OWNERS:
        tok = ORG_TOKEN if owner.lower() == "gitonboard" else TOKEN
        page = 1
        while True:
            # Try user repos first, then org repos
            url = f"{API}/users/{urllib.parse.quote(owner)}/repos?type=all&per_page=100&page={page}"
            try:
                batch = api_get(url, token=tok)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    url = f"{API}/orgs/{urllib.parse.quote(owner)}/repos?type=public&per_page=100&page={page}"
                    batch = api_get(url, token=tok)
                else:
                    print(f"WARNING: failed fetching repos for {owner}: HTTP {e.code}", file=sys.stderr)
                    break
            except Exception as e:
                print(f"WARNING: failed fetching repos for {owner}: {e}", file=sys.stderr)
                break

            if not batch:
                break
            out.extend(r for r in batch if not r.get("private", True)
                       and r.get("owner", {}).get("login", "").lower() == owner.lower())
            if len(batch) < 100:
                break
            page += 1
    return out

def card(x, width, label, value, note):
    return f"""
    <g>
      <rect x="{x}" y="118" width="{width}" height="124" rx="16" fill="#0b1722" fill-opacity=".85" stroke="#00f7ff" stroke-opacity=".3" stroke-width="1.2"/>
      <path d="M{x+16} 118 H{x+width-16}" stroke="#00f7ff" stroke-opacity=".6" stroke-width="1.5"/>
      <text x="{x+20}" y="148" fill="#7a9bb0" font-family="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" font-size="10.5" font-weight="600" letter-spacing="1.5">{escape(label)}</text>
      <text x="{x+20}" y="193" fill="#00f7ff" font-family="'JetBrains Mono', 'Fira Code', 'Segoe UI', monospace" font-size="28" font-weight="700">{escape(value)}</text>
      <text x="{x+20}" y="221" fill="#6c8899" font-family="'JetBrains Mono', 'Fira Code', 'Segoe UI', monospace" font-size="9.5" letter-spacing="0.5">{escape(note)}</text>
    </g>"""

def svg(summary, updated):
    cards = [
        card(25, 202, "ALL-TIME CLONES", f'{summary["all_time_clones"]:,}', "tracked since setup"),
        card(243, 202, "UNIQUE CLONER-DAYS", f'{summary["all_time_unique_cloner_days"]:,}', "daily uniques summed"),
        card(461, 202, "CLONES · 14 DAYS", f'{summary["rolling_14_day_clones"]:,}', "rolling API window"),
        card(679, 196, "UNIQUE · 14 DAYS", f'{summary["rolling_14_day_unique_cloner_days"]:,}', "daily uniques summed"),
    ]
    owners_label = " · ".join(OWNERS)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="340" viewBox="0 0 900 340" role="img" aria-labelledby="title desc">
<title id="title">SYSTEM // DHEERAJ - Repository Traffic</title>
<desc id="desc">Cyan cyberpunk telemetry dashboard with clone statistics for {owners_label}.</desc>
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#04090e"/><stop offset=".5" stop-color="#0d232d"/><stop offset="1" stop-color="#050e14"/></linearGradient>
 <radialGradient id="glow" cx=".5" cy="0" r="1"><stop offset="0" stop-color="#00f7ff" stop-opacity=".22"/><stop offset="1" stop-color="#00f7ff" stop-opacity="0"/></radialGradient>
</defs>
<rect width="900" height="340" rx="20" fill="url(#bg)"/><rect width="900" height="340" rx="20" fill="url(#glow)"/>
<rect x="1" y="1" width="898" height="338" rx="19" fill="none" stroke="#00f7ff" stroke-opacity=".25" stroke-width="1.2"/>
<text x="28" y="36" fill="#00f7ff" font-family="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" font-size="11" letter-spacing="3">AGENT SYSTEMS // TELEMETRY</text>
<text x="28" y="72" fill="#e7fcff" font-family="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" font-size="25" font-weight="700" letter-spacing="1">REPOSITORY TRAFFIC</text>
<text x="360" y="70" fill="#7a9bb0" font-family="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" font-size="12">[ {escape(owners_label)} ]</text>
<text x="872" y="38" text-anchor="end" fill="#00f7ff" font-family="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" font-size="11" letter-spacing="1.5">● ACTIVE</text>
<path d="M24 92 H876" stroke="#00f7ff" stroke-opacity=".35" stroke-dasharray="4 2"/>
{''.join(cards)}
<text x="28" y="275" fill="#a4dbe8" font-family="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" font-size="11.5">» {summary["repositories_successful"]} / {summary["repositories_public"]} public repos collected across @salianDheeraj &amp; @GitOnBoard</text>
<text x="28" y="297" fill="#628091" font-family="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" font-size="9.5" letter-spacing="0.5">UNIQUE COUNTS ARE DAILY PER-REPO SUMS, NOT GLOBALLY DEDUPLICATED PERSONS.</text>
<text x="28" y="321" fill="#628091" font-family="'JetBrains Mono', 'Fira Code', 'Courier New', monospace" font-size="9.5" letter-spacing="0.5">LAST SYNCED: {escape(updated)} UTC · GITHUB TRAFFIC TELEMETRY</text>
</svg>
"""

def update_readme():
    if not README_PATH.exists():
        return
    text = README_PATH.read_text(encoding="utf-8")
    block = (f"{START}\n<p align=\"center\">\n"
             "  <img src=\"assets/repo-traffic.svg\" alt=\"Repository traffic dashboard\" width=\"100%\" />\n"
             "</p>\n<p align=\"center\"><sub>All-time totals start when tracking is enabled. Unique counts are daily per-repository sums, not globally deduplicated people.</sub></p>\n"
             f"{END}")
    if START in text and END in text:
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        text = before + block + after
    else:
        text = text.rstrip() + "\n\n## ⌁ > repo_traffic\n\n" + block + "\n"
    README_PATH.write_text(text, encoding="utf-8")

def main():
    if not TOKEN:
        print("ERROR: Set TRAFFIC_TOKEN in the environment.", file=sys.stderr)
        return 2
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8")) if DATA_PATH.exists() else {
        "schema_version": 1, "owner": OWNER, "repositories": {},
        "first_collected_at": None, "notes": {
            "all_time_clones": "Tracked sum since setup, not pre-setup lifetime traffic.",
            "all_time_unique_cloner_days": "Sum of daily per-repo unique cloners, not unique people over all time."
        }
    }
    data["first_collected_at"] = data.get("first_collected_at") or now.isoformat()
    data["last_updated_at"] = now.isoformat()
    repos = public_repos()
    successes, failures = 0, []
    for repo in repos:
        full_name = repo["full_name"]
        repo_owner = repo.get("owner", {}).get("login", "")
        repo_name = repo.get("name", "")
        try:
            payload = api_get(f'{API}/repos/{urllib.parse.quote(repo_owner)}/{urllib.parse.quote(repo_name)}/traffic/clones')
            rec = data["repositories"].setdefault(full_name, {"days": {}})
            rec["url"] = repo.get("html_url", f"https://github.com/{full_name}")
            rec["last_success_at"] = now.isoformat()
            for row in payload.get("clones", []):
                day = dt.datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")).date().isoformat()
                rec["days"][day] = {"clones": int(row.get("count", 0)),
                                    "unique_cloners": int(row.get("uniques", 0)),
                                    "observed_at": now.isoformat()}
            successes += 1
        except urllib.error.HTTPError as e:
            failures.append({"repository": full_name, "status": e.code, "message": e.read().decode("utf-8", "replace")[:200]})
            print(f"WARNING {full_name}: HTTP {e.code}", file=sys.stderr)
        except Exception as e:
            failures.append({"repository": full_name, "status": "error", "message": str(e)[:200]})
            print(f"WARNING {full_name}: {e}", file=sys.stderr)
        time.sleep(.08)

    cutoff = today - dt.timedelta(days=13)
    all_clones = all_unique = recent_clones = recent_unique = history_count = 0
    for rec in data["repositories"].values():
        if rec.get("days"):
            history_count += 1
        for day_s, m in rec.get("days", {}).items():
            day = dt.date.fromisoformat(day_s)
            c, u = int(m.get("clones", 0)), int(m.get("unique_cloners", 0))
            all_clones += c
            all_unique += u
            if cutoff <= day <= today:
                recent_clones += c
                recent_unique += u
    summary = {
        "all_time_clones": all_clones,
        "all_time_unique_cloner_days": all_unique,
        "rolling_14_day_clones": recent_clones,
        "rolling_14_day_unique_cloner_days": recent_unique,
        "repositories_public": len(repos), "repositories_successful": successes,
        "repositories_with_history": history_count,
        "window_start_utc": cutoff.isoformat(), "window_end_utc": today.isoformat(),
        "updated_at_utc": now.isoformat(), "collection_failures": failures,
        "first_collected_at": data["first_collected_at"]
    }
    data.update({"owners": OWNERS, "repositories_public": len(repos),
                 "repositories_successful": successes, "collection_failures": failures,
                 "summary": summary})
    DATA_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SVG_PATH.write_text(svg(summary, now.strftime("%Y-%m-%d %H:%M")), encoding="utf-8")
    update_readme()
    print(json.dumps(summary, indent=2))
    if repos and successes == 0:
        print("ERROR: No traffic endpoints succeeded; check token permissions.", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
