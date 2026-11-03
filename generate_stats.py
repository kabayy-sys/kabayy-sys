#!/usr/bin/env python3
"""Generate assets/stats.svg — a self-hosted, animated stats card (stdlib only).

Env:
  GH_USER   GitHub username (default: kabayy-sys)
  GH_TOKEN  token for GraphQL (GITHUB_TOKEN works; a PAT with read:user adds private contributions)
  OUT       output path (default: assets/stats.svg)
  DEMO=1    render with sample data (for design preview)
"""
import datetime as dt
import html
import json
import os
import urllib.request

USER = os.environ.get("GH_USER", "kabayy-sys")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT", "assets/stats.svg")

G, C, D = "#D4AF6A", "#C0314F", "#7A1B2E"
SERIF = "Georgia, 'Times New Roman', serif"
MONO = "'Courier New', Courier, monospace"
BAR_COLORS = [C, G, "#F3DDA6", D, "#8A8A96"]
esc = html.escape


# ------------------------------------------------------------------ data
def http(url, data=None):
    headers = {"User-Agent": "stats-card", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


GQL = """
query($login:String!){ user(login:$login){
  followers{totalCount}
  pullRequests{totalCount}
  issues{totalCount}
  repositories(ownerAffiliations:OWNER,isFork:false,first:100){
    totalCount
    nodes{ stargazerCount
      languages(first:6,orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name } } } } }
  contributionsCollection{
    totalCommitContributions restrictedContributionsCount
    contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } } }
}}"""


def streaks(days):
    days = sorted(days)
    longest = run = 0
    for _, n in days:
        run = run + 1 if n > 0 else 0
        longest = max(longest, run)
    cur = 0
    seq = days[:-1] if days and days[-1][1] == 0 else days  # today may still be empty
    for _, n in reversed(seq):
        if n > 0:
            cur += 1
        else:
            break
    return cur, longest


def fetch():
    d = dict(stars=None, commits=None, prs=None, issues=None, repos=None,
             followers=None, total=None, cur=None, longest=None, langs={})
    try:  # GraphQL (needs token)
        if not TOKEN:
            raise RuntimeError("no token")
        body = json.dumps({"query": GQL, "variables": {"login": USER}}).encode()
        u = http("https://api.github.com/graphql", body)["data"]["user"]
        repos = u["repositories"]["nodes"]
        cc = u["contributionsCollection"]
        days = [(x["date"], x["contributionCount"])
                for w in cc["contributionCalendar"]["weeks"] for x in w["contributionDays"]]
        d.update(stars=sum(r["stargazerCount"] for r in repos),
                 commits=cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
                 prs=u["pullRequests"]["totalCount"], issues=u["issues"]["totalCount"],
                 repos=u["repositories"]["totalCount"], followers=u["followers"]["totalCount"],
                 total=cc["contributionCalendar"]["totalContributions"])
        d["cur"], d["longest"] = streaks(days)
        sizes = {}
        for r in repos:
            for e in r["languages"]["edges"]:
                sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]
        d["langs"] = sizes
        return d
    except Exception as e:
        print("GraphQL unavailable, falling back to REST:", e)
    try:  # REST fallback (public data only)
        u = http(f"https://api.github.com/users/{USER}")
        repos = [r for r in http(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
                 if not r["fork"]]
        sizes = {}
        for r in repos[:30]:
            try:
                for k, v in http(r["languages_url"]).items():
                    sizes[k] = sizes.get(k, 0) + v
            except Exception:
                pass
        d.update(stars=sum(r["stargazers_count"] for r in repos), repos=u["public_repos"],
                 followers=u["followers"], langs=sizes)
    except Exception as e:
        print("REST unavailable:", e)
    return d


def demo():
    return dict(stars=24, commits=1280, prs=63, issues=18, repos=14, followers=47,
                total=1534, cur=12, longest=41,
                langs={"TypeScript": 46, "Python": 28, "JavaScript": 14, "PLpgSQL": 7, "Shell": 5})


# ------------------------------------------------------------------ svg
def fmt(n):
    if n is None:
        return "—"
    return f"{n/1000:.1f}".rstrip("0").rstrip(".") + "K" if n >= 1000 else str(n)


def corners(w, h, l=10, o=4):
    return (f'<g fill="none" stroke="{G}" stroke-width="1.4" opacity=".85">'
            f'<path d="M{o} {o+l}V{o}H{o+l}"/><path d="M{w-o-l} {o}H{w-o}V{o+l}"/>'
            f'<path d="M{o} {h-o-l}V{h-o}H{o+l}"/><path d="M{w-o-l} {h-o}H{w-o}V{h-o-l}"/></g>')


def chase(w, h, color, begin):
    return (f'<rect x="1" y="1" width="{w-2}" height="{h-2}" fill="none" stroke="{color}" stroke-width="2" '
            f'pathLength="100" stroke-dasharray="16 84" filter="url(#glow)">'
            f'<animate attributeName="stroke-dashoffset" from="0" to="-100" dur="8s" begin="{begin}s" repeatCount="indefinite"/></rect>')


def frame(x, w, h, title, idx, col, begin):
    return (f'<rect width="{w}" height="{h}" fill="url(#bg)"/>'
            f'<rect x="6" y="6" width="{w-12}" height="{h-12}" fill="none" stroke="{D}" stroke-opacity=".4"/>'
            f'{chase(w, h, col, begin)}{corners(w, h)}'
            f'<g transform="translate(34 36)"><g><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="12s" repeatCount="indefinite"/>'
            f'<polygon points="0,-8 8,0 0,8 -8,0" fill="none" stroke="{G}" stroke-width="1.4"/></g>'
            f'<polygon points="0,-3 3,0 0,3 -3,0" fill="{C}"/></g>'
            f'<text x="54" y="41" font-family="{SERIF}" font-size="14" font-weight="700" letter-spacing="2" fill="url(#gold)">{title}</text>'
            f'<text x="{w-24}" y="41" text-anchor="end" font-family="{MONO}" font-size="11" letter-spacing="3" fill="{C}">{idx}</text>'
            f'<rect x="24" y="56" width="{w-48}" height="1" fill="url(#hsep)"/>')


def fade(a, b, dur=2.4):
    return f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{a};{b}" dur="{dur}s" fill="freeze"/>'


def card_overview(d):
    items = [("STARS", d["stars"]), ("COMMITS · 1Y", d["commits"]), ("PULL REQ", d["prs"]),
             ("ISSUES", d["issues"]), ("REPOS", d["repos"]), ("FOLLOWERS", d["followers"])]
    out = frame(0, 280, 250, "OVERVIEW", "01", C, 0)
    for i, (lab, val) in enumerate(items):
        x, y = 28 + (i % 2) * 124, 104 + (i // 2) * 58
        a = 0.05 + i * 0.1
        out += (f'<g>{fade(round(a,2), round(a+0.2,2))}'
                f'<text x="{x}" y="{y}" font-family="{SERIF}" font-size="26" font-weight="700" fill="url(#gold)">{fmt(val)}</text>'
                f'<text x="{x}" y="{y+17}" font-family="{MONO}" font-size="10" letter-spacing="2" fill="#9A9AA8">{lab}</text></g>')
    return out


def card_langs(d):
    out = frame(0, 280, 250, "LANGUAGES", "02", G, 1.4)
    sizes = d["langs"]
    total = sum(sizes.values())
    if not total:
        return out + (f'<text x="140" y="140" text-anchor="middle" font-family="{MONO}" font-size="11" '
                      f'letter-spacing="3" fill="#9A9AA8">SYNCING…</text>')
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:5]
    for i, (name, sz) in enumerate(top):
        pct = sz / total * 100
        y = 86 + i * 31
        w = max(3, pct / 100 * 232)
        col = BAR_COLORS[i % len(BAR_COLORS)]
        k = round(0.1 + i * 0.12, 2)
        out += (f'<text x="24" y="{y}" font-family="{MONO}" font-size="12" fill="#E8E0CE">{esc(name[:14])}</text>'
                f'<text x="256" y="{y}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{col}">{pct:.0f}%</text>'
                f'<rect x="24" y="{y+7}" width="232" height="5" fill="#1A1216"/>'
                f'<rect x="24" y="{y+7}" width="{w:.1f}" height="5" fill="{col}" filter="url(#glow)">'
                f'<animate attributeName="width" values="0;0;{w:.1f}" keyTimes="0;{k};1" dur="2.2s" fill="freeze"/></rect>')
    return out


def card_streak(d):
    out = frame(0, 280, 250, "CONTRIBUTIONS", "03", C, 2.8)
    out += (f'<g transform="translate(140 120)">'
            f'<g opacity=".8"><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="30s" repeatCount="indefinite"/>'
            f'<circle r="54" fill="none" stroke="{G}" stroke-dasharray="3 7"/></g>'
            f'<g><animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="20s" repeatCount="indefinite"/>'
            f'<polygon points="0,-45 45,0 0,45 -45,0" fill="none" stroke="{C}" stroke-width="1.4"/></g>'
            f'<text y="9" text-anchor="middle" font-family="{SERIF}" font-size="28" font-weight="700" fill="url(#gold)" filter="url(#glow)">{fmt(d["total"])}</text></g>'
            f'<text x="140" y="189" text-anchor="middle" font-family="{MONO}" font-size="10" letter-spacing="3" fill="#9A9AA8">PAST YEAR</text>'
            f'<rect x="139.5" y="200" width="1" height="38" fill="url(#hsep)"/>')
    for x, val, lab in [(80, d["cur"], "CURRENT"), (200, d["longest"], "LONGEST")]:
        v = "—" if val is None else f"{val}d"
        out += (f'<text x="{x}" y="220" text-anchor="middle" font-family="{SERIF}" font-size="20" font-weight="700" fill="url(#gold)">{v}</text>'
                f'<text x="{x}" y="236" text-anchor="middle" font-family="{MONO}" font-size="9" letter-spacing="2" fill="#9A9AA8">{lab} STREAK</text>')
    return out


def build(d):
    defs = f'''<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0D0C12"/><stop offset="1" stop-color="#170910"/></linearGradient>
<linearGradient id="gold" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#B8924A"/><stop offset=".5" stop-color="#F3DDA6"/><stop offset="1" stop-color="#B8924A"/></linearGradient>
<linearGradient id="hsep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{G}" stop-opacity="0"/><stop offset=".5" stop-color="{G}" stop-opacity=".8"/><stop offset="1" stop-color="{G}" stop-opacity="0"/></linearGradient>
<filter id="glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'''
    cards = "".join(f'<g transform="translate({i*310} 0)">{fn(d)}</g>'
                    for i, fn in enumerate([card_overview, card_langs, card_streak]))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 250" width="900" height="250" role="img" '
            f'aria-label="GitHub stats for {esc(USER)}"><defs>{defs}</defs>{cards}</svg>\n')


if __name__ == "__main__":
    data = demo() if os.environ.get("DEMO") else fetch()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(data))
    print("wrote", OUT, "@", dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
