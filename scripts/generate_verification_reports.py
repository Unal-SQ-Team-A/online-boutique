#!/usr/bin/env python3
"""Genera reportes ejecutivos HTML individuales y consolidado desde artefactos de CI."""

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


def parse_go(component: str, report_dir: Path) -> dict[str, Any]:
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
            functions.append({"label": f"{short_file}:{m_fn.group(3)}", "pct": float(m_fn.group(4))})

    def _g_int(pat: str) -> int:
        m = re.search(pat, grem_text)
        return int(m.group(1)) if m else 0

    def _g_str(pat: str, default: str = "0.00%") -> str:
        m = re.search(pat, grem_text)
        return m.group(1) if m else default

    killed = _g_int(r"Killed:\s*(\d+)")
    lived = _g_int(r"Lived:\s*(\d+)")
    not_covered = _g_int(r"Not covered:\s*(\d+)")
    timed_out = _g_int(r"Timed out:\s*(\d+)")
    efficacy = _g_str(r"Test efficacy:\s*([\d.]+%)")
    mut_cov = _g_str(r"Mutator coverage:\s*([\d.]+%)")

    passed_tests = len(re.findall(r"--- PASS:", test_text))
    failed_tests = len(re.findall(r"--- FAIL:", test_text))
    no_tests = "Sin pruebas unitarias" in test_text
    status = "SIN TESTS" if no_tests else ("PASS" if failed_tests == 0 and ("PASS" in test_text or passed_tests > 0) else "FAIL")

    return {
        "component": component,
        "stack": "Go",
        "status": status,
        "passed": passed_tests,
        "failed": failed_tests,
        "coverage": total_cov,
        "mutation_summary": "Omitida" if "Mutación omitida" in grem_text else f"Efficacy {efficacy} ({killed} Killed, {lived} Lived)",
        "killed": killed,
        "lived": lived,
        "timed_out": timed_out,
        "not_covered": not_covered,
        "efficacy": efficacy,
        "mut_cov": mut_cov,
        "functions": functions,
    }


def parse_python(component: str, report_dir: Path) -> dict[str, Any]:
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
            total_stmts, total_miss, total_cov = int(m_tot.group(1)), int(m_tot.group(2)), m_tot.group(3)
            continue
        m_mod = re.match(r"^([\w./\\-]+\.py)\s+(\d+)\s+(\d+)\s+(\d+)%", line.strip())
        if m_mod:
            modules.append({
                "name": m_mod.group(1),
                "stmts": int(m_mod.group(2)),
                "miss": int(m_mod.group(3)),
                "pct": int(m_mod.group(4)),
            })

    m_sum = re.search(r"(\d+)\s+passed", cov_text)
    passed = int(m_sum.group(1)) if m_sum else 0
    m_fail = re.search(r"(\d+)\s+failed", cov_text)
    failed = int(m_fail.group(1)) if m_fail else 0
    no_tests = "Sin pruebas unitarias" in cov_text
    status = "SIN TESTS" if no_tests else ("PASS" if failed == 0 and passed > 0 else "FAIL")

    killed = survived = timeout = suspicious = skipped = total_mutants = 0
    progress_matches = re.findall(
        r"(\d+)/(\d+)\s+🎉\s*(\d+)\s+⏰\s*(\d+)\s+🤔\s*(\d+)\s+🙁\s*(\d+)\s+🔇\s*(\d+)",
        mut_run_text,
    )
    if progress_matches:
        _, tm, k, to, su, sv, sk = progress_matches[-1]
        total_mutants, killed, timeout, suspicious, survived, skipped = int(tm), int(k), int(to), int(su), int(sv), int(sk)

    killed_pct = (killed / total_mutants * 100.0) if total_mutants > 0 else 0.0
    survived_ids = ""
    for line in mut_res_text.splitlines():
        if re.match(r"^[\d,\s-]+$", line.strip()) and line.strip():
            survived_ids = line.strip()

    return {
        "component": component,
        "stack": "Python",
        "status": status,
        "passed": passed,
        "failed": failed,
        "coverage": total_cov,
        "total_stmts": total_stmts,
        "total_miss": total_miss,
        "modules": modules,
        "killed": killed,
        "survived": survived,
        "timeout": timeout,
        "suspicious": suspicious,
        "skipped": skipped,
        "total_mutants": total_mutants,
        "killed_pct": killed_pct,
        "survived_ids": survived_ids,
        "mutation_summary": "Omitida" if "Mutación omitida" in mut_res_text else f"{killed_pct:.2f}% ({killed}/{total_mutants} Killed)",
    }


def parse_node(component: str, report_dir: Path) -> dict[str, Any]:
    test_text = _read_text(report_dir / "node-test-coverage.txt")
    stryker_text = _read_text(report_dir / "stryker-report.txt")

    no_tests = "Sin pruebas unitarias" in test_text
    m_pass = re.search(r"(?:pass|passing)\s+(\d+)", test_text, re.IGNORECASE)
    passed = int(m_pass.group(1)) if m_pass else 0
    m_cov = re.search(r"All files\s*\|\s*([\d.]+)", test_text)
    cov = f"{m_cov.group(1)}%" if m_cov else "N/A"
    status = "SIN TESTS" if no_tests else ("PASS" if "fail" not in test_text.lower() or passed > 0 else "FAIL")

    no_mut = "Sin configuración de mutación" in stryker_text
    m_stryker = re.search(r"Mutation score:\s*([\d.]+%)", stryker_text)
    mut_summary = "Sin Stryker configurado" if no_mut else (m_stryker.group(1) if m_stryker else "Ejecutado")

    return {
        "component": component,
        "stack": "Node.js",
        "status": status,
        "passed": passed,
        "failed": 0,
        "coverage": cov,
        "mutation_summary": mut_summary,
        "raw_test": test_text.strip(),
        "raw_mut": stryker_text.strip(),
    }


def parse_dotnet(component: str, report_dir: Path) -> dict[str, Any]:
    test_text = _read_text(report_dir / "dotnet-test.txt")
    stryker_text = _read_text(report_dir / "stryker-report.txt")

    m_pass = re.search(r"Passed!\s*-\s*Failed:\s*(\d+),\s*Passed:\s*(\d+)", test_text)
    if not m_pass:
        m_pass = re.search(r"Aprobadas:\s*(\d+)|Passed:\s*(\d+)", test_text)
    failed = int(m_pass.group(1)) if (m_pass and len(m_pass.groups()) >= 2 and m_pass.group(1)) else 0
    passed = int(m_pass.group(2)) if (m_pass and len(m_pass.groups()) >= 2 and m_pass.group(2)) else 0
    status = "PASS" if ("Passed!" in test_text or passed > 0) and failed == 0 else "SIN TESTS"

    no_mut = "Sin configuración de mutación" in stryker_text
    mut_summary = "Sin Stryker.NET configurado" if no_mut else "Ejecutado"

    return {
        "component": component,
        "stack": ".NET",
        "status": status,
        "passed": passed,
        "failed": failed,
        "coverage": "XPlat Cobertura XML" if status == "PASS" else "N/A",
        "mutation_summary": mut_summary,
        "raw_test": test_text.strip(),
        "raw_mut": stryker_text.strip(),
    }


def parse_auto(component: str, report_dir: Path, stack: str | None = None) -> dict[str, Any]:
    if stack == "go" or (stack is None and (report_dir / "coverage-summary.txt").exists()):
        return parse_go(component, report_dir)
    if stack == "python" or (stack is None and (report_dir / "pytest-coverage.txt").exists()):
        return parse_python(component, report_dir)
    if stack == "node" or (stack is None and (report_dir / "node-test-coverage.txt").exists()):
        return parse_node(component, report_dir)
    if stack == "dotnet" or (stack is None and (report_dir / "dotnet-test.txt").exists()):
        return parse_dotnet(component, report_dir)
    return {
        "component": component,
        "stack": stack or "Desconocido",
        "status": "SIN DATOS",
        "passed": 0,
        "failed": 0,
        "coverage": "N/A",
        "mutation_summary": "N/A",
    }


def render_component_card(d: dict[str, Any]) -> str:
    pill_cls = "pill-green" if d["status"] == "PASS" else ("pill-amber" if d["status"] == "SIN TESTS" else "pill-red")
    stack = d["stack"]

    if stack == "Go":
        bars = "".join(
            f'<div class="bar-row"><div class="bar-head"><span><code>{html.escape(fn["label"])}</code></span><span>{fn["pct"]:.1f}%</span></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{fn["pct"]:.1f}%;background:{_bar_color(fn["pct"])}"></div></div></div>'
            for fn in d.get("functions", [])
        )
        eff = float(d["efficacy"].rstrip("%") or 0)
        donut = _donut_svg(eff, d["efficacy"], "EFFICACY")
        body = f"""
        <div class="two-col">
          <div class="sub-panel"><h3>Cobertura por Función (Total: {html.escape(d['coverage'])})</h3>{bars or '<p>Sin funciones reportadas.</p>'}</div>
          <div class="sub-panel">
            <h3>Mutación (<code>gremlins</code>)</h3>
            <div class="donut-wrap">{donut}
              <ul class="donut-legend">
                <li><span><i class="dot" style="background:var(--emerald)"></i>Killed</span><strong>{d['killed']}</strong></li>
                <li><span><i class="dot" style="background:var(--rose)"></i>Lived</span><strong>{d['lived']}</strong></li>
                <li><span><i class="dot" style="background:var(--amber)"></i>Timed out</span><strong>{d['timed_out']}</strong></li>
                <li><span><i class="dot" style="background:#94a3b8"></i>Not covered</span><strong>{d['not_covered']}</strong></li>
              </ul>
            </div>
          </div>
        </div>"""
    elif stack == "Python":
        bars = "".join(
            f'<div class="bar-row"><div class="bar-head"><span><code>{html.escape(m["name"])}</code> ({m["stmts"]} stmts)</span><span>{m["pct"]}%</span></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{m["pct"]}%;background:{_bar_color(m["pct"])}"></div></div></div>'
            for m in d.get("modules", [])
        )
        donut = _donut_svg(d["killed_pct"], f"{d['killed_pct']:.1f}%", "KILLED", track_color="#fee2e2")
        body = f"""
        <div class="two-col">
          <div class="sub-panel"><h3>Cobertura por Módulo (Total: {html.escape(d['coverage'])})</h3>{bars or '<p>Sin módulos reportados.</p>'}</div>
          <div class="sub-panel">
            <h3>Mutación (<code>mutmut</code> · {d['total_mutants']} mutantes)</h3>
            <div class="donut-wrap">{donut}
              <ul class="donut-legend">
                <li><span><i class="dot" style="background:var(--emerald)"></i>Killed</span><strong>{d['killed']} ({d['killed_pct']:.2f}%)</strong></li>
                <li><span><i class="dot" style="background:var(--rose)"></i>Survived</span><strong>{d['survived']}</strong></li>
                <li><span><i class="dot" style="background:var(--amber)"></i>Timeout / Skipped</span><strong>{d['timeout'] + d['suspicious'] + d['skipped']}</strong></li>
              </ul>
            </div>
            <p style="font-size:12px;color:var(--muted);margin:10px 0 0;">Sobrevivientes: <code>{html.escape(d['survived_ids'] or 'N/A')}</code></p>
          </div>
        </div>"""
    else:
        body = f"""
        <div class="two-col">
          <div class="sub-panel"><h3>Pruebas y Cobertura</h3><p>Estado: <strong>{html.escape(d['status'])}</strong> · Cobertura: <strong>{html.escape(d['coverage'])}</strong></p></div>
          <div class="sub-panel"><h3>Mutación</h3><p>{html.escape(d['mutation_summary'])}</p></div>
        </div>"""

    return f"""
    <section class="section-card">
      <div class="section-header">
        <h2 class="section-title"><span class="comp-badge">{html.escape(stack)}</span> {html.escape(d['component'])}</h2>
        <span class="pill {pill_cls}">{html.escape(d['status'])} · {html.escape(d['mutation_summary'])}</span>
      </div>
      {body}
    </section>"""


def wrap_page(title: str, eyebrow: str, heading: str, subtitle: str, meta: list[tuple[str, str]], kpis: str, body: str) -> str:
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
    <header class="hero">
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
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera reportes ejecutivos HTML individuales y consolidado.")
    parser.add_argument("--component", help="Nombre del componente individual")
    parser.add_argument("--stack", choices=["go", "python", "node", "dotnet"], help="Stack del componente")
    parser.add_argument("--report-dir", type=Path, help="Directorio de reportes de un componente")
    parser.add_argument("--reports-root", type=Path, help="Directorio padre con carpetas *-verification-reports")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directorio de salida")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    now_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if args.component and args.report_dir:
        d = parse_auto(args.component, args.report_dir, args.stack)
        kpis = f"""
        <div class="kpi-card"><div class="kpi-label">Estado Pruebas</div><div class="kpi-value">{html.escape(d['status'])}</div><div class="kpi-sub">Pass: {d['passed']} · Fail: {d['failed']}</div></div>
        <div class="kpi-card"><div class="kpi-label">Cobertura</div><div class="kpi-value">{html.escape(d['coverage'])}</div><div class="kpi-sub">Stack: {html.escape(d['stack'])}</div></div>
        <div class="kpi-card"><div class="kpi-label">Mutación</div><div class="kpi-value" style="font-size:20px;">{html.escape(d['mutation_summary'])}</div><div class="kpi-sub">Ejecución automática CI</div></div>
        """
        doc = wrap_page(
            f"Informe Ejecutivo — {d['component']}",
            f"Verificación de Componente · {d['stack']}",
            f"Informe Ejecutivo — {d['component']}",
            "Reporte automático de pruebas unitarias, cobertura y mutación.",
            [("Componente", d["component"]), ("Stack", d["stack"]), ("Generado", now_str)],
            kpis,
            render_component_card(d),
        )
        (args.output_dir / "executive-report.html").write_text(doc, encoding="utf-8")
        return

    if args.reports_root:
        components: list[dict[str, Any]] = []
        for sub in sorted(args.reports_root.iterdir()):
            if sub.is_dir():
                comp_name = sub.name.removesuffix("-verification-reports")
                components.append(parse_auto(comp_name, sub))

        summary_rows = "".join(
            f"<tr><td><strong>{html.escape(c['component'])}</strong></td><td><code>{html.escape(c['stack'])}</code></td>"
            f"<td><span class='pill {'pill-green' if c['status']=='PASS' else 'pill-amber'}'>{html.escape(c['status'])}</span></td>"
            f"<td>{html.escape(c['coverage'])}</td><td>{html.escape(c['mutation_summary'])}</td></tr>"
            for c in components
        )
        summary_table = f"""
        <section class="section-card">
          <div class="section-header"><h2 class="section-title">Resumen General de Componentes</h2></div>
          <table>
            <thead><tr><th>Componente</th><th>Stack</th><th>Pruebas</th><th>Cobertura</th><th>Mutación</th></tr></thead>
            <tbody>{summary_rows}</tbody>
          </table>
        </section>"""

        cards = summary_table + "".join(render_component_card(c) for c in components)
        pass_cnt = sum(1 for c in components if c["status"] == "PASS")
        kpis = f"""
        <div class="kpi-card"><div class="kpi-label">Componentes Evaluados</div><div class="kpi-value">{len(components)}</div><div class="kpi-sub">Ejecutados en este flujo</div></div>
        <div class="kpi-card"><div class="kpi-label">Suites en PASS</div><div class="kpi-value">{pass_cnt}</div><div class="kpi-sub">De {len(components)} componentes</div></div>
        <div class="kpi-card"><div class="kpi-label">Fecha de Corte</div><div class="kpi-value" style="font-size:20px;">{now_str}</div><div class="kpi-sub">GitHub Actions CI</div></div>
        """
        doc = wrap_page(
            "Reporte Ejecutivo Consolidado — Online Boutique",
            "Entregable 1 · Verificación a Nivel de Componente",
            "Reporte Ejecutivo Consolidado de Cobertura y Mutación",
            "Resumen automático de pruebas unitarias, cobertura y mutación para todos los componentes ejecutados.",
            [("Sistema", "Online Boutique"), ("Componentes", str(len(components))), ("Generado", now_str)],
            kpis,
            cards,
        )
        (args.output_dir / "executive-verification-report.html").write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    main()
