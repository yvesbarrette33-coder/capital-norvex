"""Émile — template HTML brief pré-call (style Norvex premium 1 page)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


def render_html_brief(
    target: Dict[str, Any],
    engagement: Dict[str, Any],
    advisor_output: Dict[str, Any],
) -> str:
    """Génère le brief HTML complet à partir des composantes.

    Style verrouillé : Georgia + Arial + #b8975a / #0a0d13 / #faf8f4 / #c73c2e.
    Format lettre US, 1 page, marges 18mm.
    """
    name = target.get("name") or "Cible"
    org = target.get("organization") or ""
    title = target.get("title") or ""
    region = target.get("region") or ""
    cap = target.get("capitalEstimate") or {}
    cap_str = (
        f"{cap.get('min', 0)/1e6:.0f}M – {cap.get('max', 0)/1e6:.0f}M$"
        if cap.get("min") else "—"
    )
    thesis = target.get("investmentThesis") or ""

    perso = engagement.get("perso", {})
    primary_email = engagement.get("primary_email", "")
    perso_opens = perso.get("opens", 0)
    perso_clicks = perso.get("clicks", 0)
    org_total_clicks = engagement.get("total_clicks", 0)
    org_total_opens = engagement.get("total_opens", 0)
    org_contacts = len(engagement.get("org_contacts", []))

    lecture = advisor_output.get("lecture_analytique", "")
    theses = advisor_output.get("theses_co_financement", [])
    talking_points = advisor_output.get("talking_points", [])
    donts = advisor_output.get("donts", [])

    today = datetime.now().strftime("%Y-%m-%d")

    theses_html = "\n".join(f"<li>{t}</li>" for t in theses)
    tp_html = "\n".join(f"<li>{p}</li>" for p in talking_points)
    donts_html = "\n".join(f"<li>{d}</li>" for d in donts)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Brief pré-call — {name} — Capital Norvex</title>
<style>
  @page {{ size: letter; margin: 18mm; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: Georgia, 'Times New Roman', serif;
    color: #0a0d13;
    background: #faf8f4;
    margin: 0;
    padding: 28px 36px;
    line-height: 1.55;
    font-size: 13.5px;
  }}
  .header {{
    border-bottom: 2px solid #b8975a;
    padding-bottom: 10px;
    margin-bottom: 18px;
  }}
  .kicker {{
    font-size: 10px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #b8975a;
    font-family: Arial, sans-serif;
  }}
  h1 {{
    font-size: 22px;
    margin: 4px 0 0 0;
    font-weight: normal;
  }}
  h1 em {{ color: #b8975a; font-style: italic; }}
  h2 {{
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #0a0d13;
    border-bottom: 1px solid #d4c298;
    padding-bottom: 3px;
    margin: 18px 0 8px 0;
    font-family: Arial, sans-serif;
  }}
  .signal-row {{
    display: flex;
    gap: 8px;
    margin: 8px 0;
  }}
  .signal {{
    flex: 1;
    background: #fff;
    border: 1px solid #e3d9c0;
    padding: 8px 10px;
    border-radius: 3px;
  }}
  .signal .num {{
    font-size: 22px;
    color: #b8975a;
    font-weight: bold;
    font-family: Arial, sans-serif;
    font-variant-numeric: tabular-nums lining-nums;
  }}
  .signal .label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #6c6356;
    font-family: Arial, sans-serif;
  }}
  ul {{ padding-left: 18px; margin: 6px 0 12px 0; }}
  li {{ margin-bottom: 4px; }}
  .talking-points {{
    background: #fff;
    border-left: 3px solid #b8975a;
    padding: 10px 14px;
    margin: 8px 0;
  }}
  .talking-points li::marker {{ color: #b8975a; }}
  .danger {{
    background: #fff5f0;
    border-left: 3px solid #c73c2e;
    padding: 10px 14px;
    margin: 8px 0;
  }}
  .danger ul li::marker {{ color: #c73c2e; }}
  .footer {{
    margin-top: 22px;
    padding-top: 10px;
    border-top: 1px solid #d4c298;
    font-size: 10.5px;
    color: #6c6356;
    text-align: center;
    font-family: Arial, sans-serif;
    letter-spacing: 1px;
  }}
  strong {{ color: #0a0d13; }}
  .meta-line {{
    font-size: 11px;
    color: #6c6356;
    margin-top: 6px;
    font-family: Arial, sans-serif;
  }}
  .lecture {{
    font-size: 12px;
    color: #4a4337;
    background: #fff;
    border: 1px solid #e3d9c0;
    padding: 10px 14px;
    border-radius: 3px;
    margin-top: 8px;
  }}
</style>
</head>
<body>

<div class="header">
  <div class="kicker">Émile · Norvex Briefing™ · Confidentiel</div>
  <h1>{name} — <em>{org}</em></h1>
  <div class="meta-line">
    {title or "—"} · {region or "—"} · Capital estimé : {cap_str} · Mis à jour {today}
  </div>
</div>

<h2>Profil &amp; Thèse</h2>
<p>{thesis or "Profil business à enrichir."}</p>

<h2>Signal d'intérêt — Engagement Capital Norvex</h2>
<div class="signal-row">
  <div class="signal">
    <div class="num">{perso_opens}</div>
    <div class="label">Opens — email perso</div>
  </div>
  <div class="signal">
    <div class="num">{perso_clicks}</div>
    <div class="label">Clicks — email perso</div>
  </div>
  <div class="signal">
    <div class="num">{org_total_opens}</div>
    <div class="label">Opens — domaine</div>
  </div>
  <div class="signal">
    <div class="num">{org_total_clicks}</div>
    <div class="label">Clicks — domaine</div>
  </div>
</div>
<div class="meta-line">Contact principal : {primary_email or "—"} · {org_contacts} contact(s) actif(s) sur le domaine</div>

<h2>Lecture analytique du board</h2>
<div class="lecture">{lecture}</div>

<h2>Thèses de co-financement plausibles</h2>
<ul>
{theses_html}
</ul>

<h2>Talking points si {name.split()[0]} appelle</h2>
<div class="talking-points">
<ol>
{tp_html}
</ol>
</div>

<h2>Ce qu'il faut <span style="color:#c73c2e;">PAS</span> faire</h2>
<div class="danger">
<ul>
{donts_html}
</ul>
</div>

<div class="footer">
  ÉMILE · NORVEX BRIEFING™ · CAPITAL NORVEX INC. · 2705-1000 ANDRÉ-PRÉVOST · CAPITALNORVEX.COM
</div>

</body>
</html>"""
