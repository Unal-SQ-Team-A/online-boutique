#!/usr/bin/env python3
"""Genera reportes ejecutivos HTML individuales y consolidado desde salidas de CI."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
from pathlib import Path
from typing import Any


BASE_CSS = """
:root {
  --bg: #f4f6fa;
  --surface: #ffffff;
  --surface-alt: #f8fafc;
  --ink: #0f172a;
  --muted: #475569;
  --line: #e2e8f0;
  --navy: #0f2942;
  --navy-2: #1e3a5f;
  --accent: #2563eb;
  --emerald: #059669;
  --emerald-bg: #ecfdf5;
  --amber: #d97706;
  --amber-bg: #fffbeb;
  --rose: #dc2626;
  --rose-bg: #fef2f2;
  --indigo: #4f46e5;
  --indigo-bg: #eef2ff;
  --shadow: 0 4px 20px rgba(15, 23, 42, 0.06);
  --radius: 14px;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.55;
}
.container { max-width: 1140px; margin: 0 auto; padding: 28px 22px 48px; }
.hero {
  background: linear-gradient(135deg, var(--navy) 0%, var(--navy-2) 65%, #1d4ed8 100%);
  color: #fff;
  border-radius: 18px;
  padding: 30px 34px;
  box-shadow: 0 12px 32px rgba(15, 41, 66, 0.22);
  margin-bottom: 22px;
}
.hero.indigo { background: linear-gradient(135deg, #1e1b4b 0%, #312e81 60%, #2563eb 100%); }
.hero-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
.eyebrow {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.09em;
  text-transform: uppercase; background: rgba(255,255,255,0.16); padding: 4px 12px;
  border-radius: 999px; margin-bottom: 10px;
}
.hero h1 { margin: 0 0 8px; font-size: 26px; }
.hero p { margin: 0; color: rgba(255,255,255,0.86); font-size: 14px; max-width: 720px; }
.hero-meta {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px;
  margin-top: 20px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.18); font-size: 13px;
}
.hero-meta span { display: block; font-size: 11px; text-transform: uppercase; color: rgba(255,255,255,0.7); }
.print-btn {
  background: #fff; color: var(--navy); border: none; padding: 10px 16px; border-radius: 10px;
  font-weight: 600; font-size: 13px; cursor: pointer;
}
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 16px; margin-bottom: 22px; }
.kpi-card {
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 18px 20px; box-shadow: var(--shadow);
}
.kpi-label { font-size: 11.5px; font-weight: 700; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }
.kpi-value { font-size: 28px; font-weight: 800; color: var(--ink); line-height: 1.1; }
.kpi-sub { margin-top: 7px; font-size: 12.5px; color: var(--muted); }
.pill { display: inline-flex; padding: 3px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 700; }
.pill-green { background: var(--emerald-bg); color: var(--emerald); }
.pill-amber { background: var(--amber-bg); color: var(--amber); }
.pill-red { background: var(--rose-bg); color: var(--rose); }
.pill-blue { background: var(--indigo-bg); color: var(--indigo); }
.section-card {
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 24px 26px; box-shadow: var(--shadow); margin-bottom: 22px;
}
.section-header {
  display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;
  padding-bottom: 12px; margin-bottom: 18px; border-bottom: 1px solid var(--line);
}
.section-title { margin: 0; font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
.comp-badge { background: var(--navy); color: #fff; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 8px; }
.two-col { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
.sub-panel { background: var(--surface-alt); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; }
.sub-panel h3 { margin: 0 0 12px; font-size: 13.5px; color: var(--navy); text-transform: uppercase; letter-spacing: 0.04em; }
.bar-row { margin-bottom: 10px; }
.bar-head { display: flex; justify-content: space-between; font-size: 12.5px; font-weight: 600; margin-bottom: 4px; gap: 8px; }
.bar-track { height: 9px; background: #e2e8f0; border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; }
.donut-wrap { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.donut-legend { list-style: none; margin: 0; padding: 0; font-size: 13px; flex: 1; min-width: 180px; }
.donut-legend li { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dashed var(--line); }
.donut-legend li:last-child { border-bottom: none; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 7px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th {
  text-align: left; font-size: 11px; text-transform: uppercase; color: var(--muted);
  background: var(--surface-alt); padding: 9px 10px; border-bottom: 2px solid var(--line);
}
td { padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
code { font-family: ui-monospace, Consolas, monospace; font-size: 12px; background: #f1f5f9; padding: 2px 5px; border-radius: 4px; }
.footer { text-align: center; font-size: 12px; color: var(--muted); margin-top: 14px; }
@media print {
  body { background: #fff; }
  .container { max-width: 100%; padding: 0; }
  .print-btn { display: none; }
  .hero, .section-card, .kpi-card { box-shadow: none; break-inside: avoid; }
}
"""


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def parse_shipping(report_dir: Path) -> dict[str, Any]:
    cov_text = _read_text(report_dir / "coverage-summary.txt")
    grem_text = _read_text(report_dir / "gremlins-report.txt")
    test_text = _read_text(report_dir / "test-results.txt")

    functions: list[dict[str, Any]] = []
    total_cov = "0.0%"
    for line in cov_text.splitlines():
        m_total = re.match(r"^total:\s+\(statements\)\s+([\d.]+%)", line.strip())
        if m_total:
            total_cov = m_total.group(1)
            continue
        m_fn = re.match(r"^(.+?):(\d+):\s+(\S+)\s+([\d.]+)%", line.strip())
        if m_fn:
            short_file = m_fn.group(1).rsplit("/", 1)[-1]
            functions.append({
                "label": f"{short_file}:{m_fn.group(3)}",
                "pct": float(m_fn.group(4)),
            })

    def _grem_int(pattern: str) -> int:
        m = re.search(pattern, grem_text)
        return int(m.group(1)) if m else 0

    def _grem_str(pattern: str, default: str = "0.00%") -> str:
        m = re.search(pattern, grem_text)
        return m.group(1) if m else default

    killed = _grem_int(r"Killed:\s*(\d+)")
    lived = _grem_int(r"Lived:\s*(\d+)")
    not_covered = _grem_int(r"Not covered:\s*(\d+)")
    timed_out = _grem_int(r"Timed out:\s*(\d+)")
    efficacy = _grem_str(r"Test efficacy:\s*([\d.]+%)")
    mut_cov = _grem_str(r"Mutator coverage:\s*([\d.]+%)")

    passed_tests = len(re.findall(r"--- PASS:", test_text))
    failed_tests = len(re.findall(r"--- FAIL:", test_text))
    overall_pass = "FAIL" not in test_text and ("PASS" in test_text or passed_tests > 0)

    return {
        "total_cov": total_cov,
        "functions": functions,
        "killed": killed,
        "lived": lived,
        "not_covered": not_covered,
        "timed_out": timed_out,
        "efficacy": efficacy,
        "mut_cov": mut_cov,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "overall_pass": overall_pass,
    }


def parse_recommendation(report_dir: Path) -> dict[str, Any]:
    cov_text = _read_text(report_dir / "pytest-coverage.txt")
    mut_res_text = _read_text(report_dir / "mutmut-results.txt")
    mut_run_text = _read_text(report_dir / "mutmut-run.txt")

    modules: list[dict[str, Any]] = []
    total_cov = "0%"
    total_stmts = 0
    total_miss = 0
    for line in cov_text.splitlines():
        m_tot = re.match(r"^TOTAL\s+(\d+)\s+(\d+)\s+(\d+%)", line.strip())
        if m_tot:
            total_stmts = int(m_tot.group(1))
            total_miss = int(m_tot.group(2))
            total_cov = m_tot.group(3)
            continue
        m_mod = re.match(r"^([\w./\\-]+\.py)\s+(\d+)\s+(\d+)\s+(\d+)%", line.strip())
        if m_mod:
            modules.append({
                "name": m_mod.group(1),
                "stmts": int(m_mod.group(2)),
                "miss": int(m_mod.group(3)),
                "pct": int(m_mod.group(4)),
            })

    tests: list[dict[str, str]] = []
    for line in cov_text.splitlines():
        m_t = re.match(r"^tests/[\w_]+\.py::(\S+)\s+(PASSED|FAILED|SKIPPED)", line.strip())
        if m_t:
            tests.append({"name": m_t.group(1), "status": m_t.group(2)})

    m_summary = re.search(r"(\d+)\s+passed", cov_text)
    passed_count = int(m_summary.group(1)) if m_summary else len([t for t in tests if t["status"] == "PASSED"])
    m_failed = re.search(r"(\d+)\s+failed", cov_text)
    failed_count = int(m_failed.group(1)) if m_failed else 0

    # Parse mutmut counts from last progress line in mutmut-run.txt
    killed = 0
    survived = 0
    timeout = 0
    suspicious = 0
    skipped = 0
    progress_matches = re.findall(
        r"(\d+)/(\d+)\s+🎉\s*(\d+)\s+⏰\s*(\d+)\s+🤔\s*(\d+)\s+🙁\s*(\d+)\s+🔇\s*(\d+)",
        mut_run_text,
    )
    if progress_matches:
        _, total_m, k, to, su, sv, sk = progress_matches[-1]
        total_mutants = int(total_m)
        killed, timeout, suspicious, survived, skipped = int(k), int(to), int(su), int(sv), int(sk)
    else:
        m_surv = re.search(r"Survived.*?\((\d+)\)", mut_res_text)
        survived = int(m_surv.group(1)) if m_surv else 0
        total_mutants = survived

    killed_pct = (killed / total_mutants * 100.0) if total_mutants > 0 else 0.0

    survived_ids = ""
    for line in mut_res_text.splitlines():
        if re.match(r"^[\d,\s-]+$", line.strip()) and line.strip():
            survived_ids = line.strip()

    return {
        "total_cov": total_cov,
        "total_stmts": total_stmts,
        "total_miss": total_miss,
        "modules": modules,
        "tests": tests,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "killed": killed,
        "survived": survived,
        "timeout": timeout,
        "suspicious": suspicious,
        "skipped": skipped,
        "total_mutants": total_mutants,
        "killed_pct": killed_pct,
        "survived_ids": survived_ids,
    }


def _bar_color(pct: float) -> str:
    if pct >= 80:
        return "var(--emerald)"
    if pct >= 40:
        return "var(--accent)"
    return "#94a3b8"


def _donut_svg(pct: float, label: str, sublabel: str, track_color: str = "#e2e8f0") -> str:
    pct_clamped = max(0.0, min(100.0, pct))
    rem = 100.0 - pct_clamped
    return f"""
    <svg width="128" height="128" viewBox="0 0 42 42">
      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="{track_color}" stroke-width="5"></circle>
      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="#059669" stroke-width="5"
              stroke-dasharray="{pct_clamped:.2f} {rem:.2f}" stroke-dashoffset="25"></circle>
      <text x="21" y="20.5" text-anchor="middle" font-size="6.8" font-weight="800" fill="#0f172a">{html.escape(label)}</text>
      <text x="21" y="26.5" text-anchor="middle" font-size="3.6" font-weight="600" fill="#475569">{html.escape(sublabel)}</text>
    </svg>
    """


def render_shipping_section(data: dict[str, Any]) -> str:
    bars_html = ""
    for fn in data["functions"]:
        color = _bar_color(fn["pct"])
        bars_html += f"""
        <div class="bar-row">
          <div class="bar-head"><span><code>{html.escape(fn['label'])}</code></span><span>{fn['pct']:.1f}%</span></div>
          <div class="bar-track"><div class="bar-fill" style="width:{fn['pct']:.1f}%;background:{color}"></div></div>
        </div>"""

    eff_num = float(data["efficacy"].rstrip("%") or 0)
    donut = _donut_svg(eff_num, data["efficacy"], "EFFICACY")

    return f"""
    <section class="section-card">
      <div class="section-header">
        <h2 class="section-title"><span class="comp-badge">C-LOG-1</span> ShippingService (Go)</h2>
        <span class="pill pill-green">Test Efficacy: {html.escape(data['efficacy'])} ({data['lived']} Lived)</span>
      </div>
      <div class="two-col">
        <div class="sub-panel">
          <h3>Cobertura por Función (Total: {html.escape(data['total_cov'])})</h3>
          {bars_html}
        </div>
        <div class="sub-panel">
          <h3>Resultados <code>gremlins unleash</code></h3>
          <div class="donut-wrap">
            {donut}
            <ul class="donut-legend">
              <li><span><i class="dot" style="background:var(--emerald)"></i>Killed</span><strong>{data['killed']}</strong></li>
              <li><span><i class="dot" style="background:var(--rose)"></i>Lived</span><strong>{data['lived']}</strong></li>
              <li><span><i class="dot" style="background:var(--amber)"></i>Timed out</span><strong>{data['timed_out']}</strong></li>
              <li><span><i class="dot" style="background:#94a3b8"></i>Not covered</span><strong>{data['not_covered']}</strong></li>
            </ul>
          </div>
          <p style="font-size:12.5px;color:var(--muted);margin:12px 0 0;">
            Mutator coverage: <strong>{html.escape(data['mut_cov'])}</strong> · Pruebas PASS: <strong>{data['passed_tests']}</strong> · FAIL: <strong>{data['failed_tests']}</strong>.
          </p>
        </div>
      </div>
    </section>
    """


def render_recommendation_section(data: dict[str, Any]) -> str:
    bars_html = ""
    for mod in data["modules"]:
        color = _bar_color(mod["pct"])
        bars_html += f"""
        <div class="bar-row">
          <div class="bar-head"><span><code>{html.escape(mod['name'])}</code> ({mod['stmts']} stmts)</span><span>{mod['pct']}%</span></div>
          <div class="bar-track"><div class="bar-fill" style="width:{mod['pct']}%;background:{color}"></div></div>
        </div>"""

    donut = _donut_svg(data["killed_pct"], f"{data['killed_pct']:.1f}%", "KILLED", track_color="#fee2e2")
    tests_rows = "".join(
        f"<tr><td><code>{html.escape(t['name'])}</code></td><td><span class='pill pill-green'>{html.escape(t['status'])}</span></td></tr>"
        for t in data["tests"]
    )

    return f"""
    <section class="section-card">
      <div class="section-header">
        <h2 class="section-title"><span class="comp-badge">C-LOG-2</span> RecommendationService (Python)</h2>
        <span class="pill pill-blue">{data['passed_count']} Passed · Cobertura Total: {html.escape(data['total_cov'])}</span>
      </div>
      <div class="two-col">
        <div class="sub-panel">
          <h3>Cobertura por Módulo ({data['total_stmts']} stmts, {data['total_miss']} miss)</h3>
          {bars_html}
        </div>
        <div class="sub-panel">
          <h3>Resultados <code>mutmut</code> ({data['total_mutants']} mutantes)</h3>
          <div class="donut-wrap">
            {donut}
            <ul class="donut-legend">
              <li><span><i class="dot" style="background:var(--emerald)"></i>Killed</span><strong>{data['killed']} ({data['killed_pct']:.2f}%)</strong></li>
              <li><span><i class="dot" style="background:var(--rose)"></i>Survived</span><strong>{data['survived']}</strong></li>
              <li><span><i class="dot" style="background:var(--amber)"></i>Timeout / Suspicious / Skipped</span><strong>{data['timeout'] + data['suspicious'] + data['skipped']}</strong></li>
            </ul>
          </div>
          <p style="font-size:12.5px;color:var(--muted);margin:12px 0 0;">
            IDs sobrevivientes en <code>recommendation_server.py</code>: <code>{html.escape(data['survived_ids'] or 'N/A')}</code>
          </p>
        </div>
      </div>
      <table style="margin-top:16px;">
        <thead><tr><th>Caso de Prueba</th><th>Veredicto</th></tr></thead>
        <tbody>{tests_rows}</tbody>
      </table>
    </section>
    """


def wrap_page(title: str, eyebrow: str, heading: str, subtitle: str, meta: list[tuple[str, str]], kpis: str, body: str, hero_class: str = "") -> str:
    meta_html = "".join(f"<div><span>{html.escape(k)}</span><strong>{html.escape(v)}</strong></div>" for k, v in meta)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)}</title>
  <style>{BASE_CSS}</style>
</head>
<body>
  <div class="container">
    <header class="hero {hero_class}">
      <div class="hero-top">
        <div>
          <span class="eyebrow">{html.escape(eyebrow)}</span>
          <h1>{html.escape(heading)}</h1>
          <p>{html.escape(subtitle)}</p>
        </div>
        <button class="print-btn" onclick="window.print()">Exportar / Imprimir PDF</button>
      </div>
      <div class="hero-meta">{meta_html}</div>
    </header>
    <section class="kpi-grid">{kpis}</section>
    {body}
    <footer class="footer">Generado automáticamente por <code>scripts/generate_verification_reports.py</code> en GitHub Actions.</footer>
  </div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera reportes ejecutivos HTML desde artefactos de CI.")
    parser.add_argument("--shipping-dir", type=Path, help="Directorio con reportes de shippingservice")
    parser.add_argument("--recommendation-dir", type=Path, help="Directorio con reportes de recommendationservice")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directorio destino para los HTML")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    now_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    ship_data = parse_shipping(args.shipping_dir) if args.shipping_dir else None
    rec_data = parse_recommendation(args.recommendation_dir) if args.recommendation_dir else None

    if ship_data:
        kpis = f"""
        <div class="kpi-card"><div class="kpi-label">Pruebas Go</div><div class="kpi-value">{'PASS' if ship_data['overall_pass'] else 'FAIL'}</div><div class="kpi-sub">{ship_data['passed_tests']} subpruebas ejecutadas</div></div>
        <div class="kpi-card"><div class="kpi-label">Cobertura Paquete</div><div class="kpi-value">{html.escape(ship_data['total_cov'])}</div><div class="kpi-sub"><code>go tool cover -func</code></div></div>
        <div class="kpi-card"><div class="kpi-label">Test Efficacy</div><div class="kpi-value">{html.escape(ship_data['efficacy'])}</div><div class="kpi-sub">{ship_data['killed']} Killed · {ship_data['lived']} Lived</div></div>
        <div class="kpi-card"><div class="kpi-label">Mutator Coverage</div><div class="kpi-value">{html.escape(ship_data['mut_cov'])}</div><div class="kpi-sub">{ship_data['not_covered']} Not covered</div></div>
        """
        html_doc = wrap_page(
            "Informe Ejecutivo — ShippingService (C-LOG-1)",
            "Componente C-LOG-1 · Capa Lógica (Go)",
            "Informe Ejecutivo — ShippingService",
            "Reporte automático de pruebas unitarias, cobertura y mutación con gremlins.",
            [("Ubicación", "src/shippingservice"), ("Herramienta", "go test + gremlins"), ("Generado", now_str)],
            kpis,
            render_shipping_section(ship_data),
        )
        (args.output_dir / "executive-report.html").write_text(html_doc, encoding="utf-8")

    if rec_data:
        kpis = f"""
        <div class="kpi-card"><div class="kpi-label">Pruebas Pytest</div><div class="kpi-value">{rec_data['passed_count']} PASSED</div><div class="kpi-sub">{rec_data['failed_count']} failed</div></div>
        <div class="kpi-card"><div class="kpi-label">Cobertura Total</div><div class="kpi-value">{html.escape(rec_data['total_cov'])}</div><div class="kpi-sub">{rec_data['total_stmts']} stmts · {rec_data['total_miss']} miss</div></div>
        <div class="kpi-card"><div class="kpi-label">Mutación (Killed)</div><div class="kpi-value">{rec_data['killed_pct']:.2f}%</div><div class="kpi-sub">{rec_data['killed']} / {rec_data['total_mutants']} mutantes</div></div>
        <div class="kpi-card"><div class="kpi-label">Sobrevivientes</div><div class="kpi-value">{rec_data['survived']}</div><div class="kpi-sub"><code>mutmut results</code></div></div>
        """
        html_doc = wrap_page(
            "Informe Ejecutivo — RecommendationService (C-LOG-2)",
            "Componente C-LOG-2 · Capa Lógica (Python)",
            "Informe Ejecutivo — RecommendationService",
            "Reporte automático de pruebas unitarias, cobertura con pytest-cov y mutación con mutmut.",
            [("Ubicación", "src/recommendationservice"), ("Herramienta", "pytest + mutmut"), ("Generado", now_str)],
            kpis,
            render_recommendation_section(rec_data),
            hero_class="indigo",
        )
        out_name = "executive-report-recommendation.html" if ship_data else "executive-report.html"
        (args.output_dir / out_name).write_text(html_doc, encoding="utf-8")

    if ship_data and rec_data:
        kpis = f"""
        <div class="kpi-card"><div class="kpi-label">ShippingService</div><div class="kpi-value">{'PASS' if ship_data['overall_pass'] else 'FAIL'}</div><div class="kpi-sub">Cobertura {html.escape(ship_data['total_cov'])} · Efficacy {html.escape(ship_data['efficacy'])}</div></div>
        <div class="kpi-card"><div class="kpi-label">RecommendationService</div><div class="kpi-value">{rec_data['passed_count']} PASSED</div><div class="kpi-sub">Cobertura {html.escape(rec_data['total_cov'])} · Killed {rec_data['killed_pct']:.2f}%</div></div>
        <div class="kpi-card"><div class="kpi-label">Mutantes Eliminados</div><div class="kpi-value">{ship_data['killed'] + rec_data['killed']}</div><div class="kpi-sub">Shipping ({ship_data['killed']}) + Recommendation ({rec_data['killed']})</div></div>
        <div class="kpi-card"><div class="kpi-label">Mutantes Sobrevivientes</div><div class="kpi-value">{ship_data['lived'] + rec_data['survived']}</div><div class="kpi-sub">Shipping ({ship_data['lived']}) + Recommendation ({rec_data['survived']})</div></div>
        """
        combined_body = render_shipping_section(ship_data) + render_recommendation_section(rec_data)
        html_doc = wrap_page(
            "Reporte Ejecutivo Consolidado — Verificación a Nivel de Componente",
            "Entregable 1 · Verificación a Nivel de Componente",
            "Reporte Ejecutivo de Cobertura y Mutación",
            "Consolidado automático generado desde los resultados de ejecución de CI para ShippingService y RecommendationService.",
            [("Sistema", "Online Boutique"), ("Componentes", "C-LOG-1, C-LOG-2"), ("Generado", now_str)],
            kpis,
            combined_body,
        )
        (args.output_dir / "executive-verification-report.html").write_text(html_doc, encoding="utf-8")


if __name__ == "__main__":
    main()
