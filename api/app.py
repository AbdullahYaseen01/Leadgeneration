import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import io
import csv as csv_module
import logging
import os
import uuid
from pathlib import Path
from threading import Thread

from flask import Flask, Response, jsonify, render_template_string, request, send_file

LEADS_FORM_JS = r"""
(function () {
  var form = document.getElementById('form');
  var btn = document.getElementById('btn');
  var msg = document.getElementById('message');
  var maxLeads = parseInt(form.getAttribute('data-max-leads'), 10) || 1000;

  var params = new URLSearchParams(window.location.search);
  var urlCities = params.getAll('city').map(function (c) { try { return decodeURIComponent(c); } catch (e) { return c; } });
  var urlNiches = params.getAll('niche').map(function (n) { try { return decodeURIComponent(n); } catch (e) { return n; } });
  var urlMax = parseInt(params.get('max_leads'), 10);
  var cityEl = document.getElementById('city');
  var nicheEl = document.getElementById('niche');
  var maxEl = document.getElementById('max_leads');
  var cityTopBtn = document.getElementById('city-top-20');
  var cityAllBtn = document.getElementById('city-all');
  var cityClearBtn = document.getElementById('city-clear');
  var nicheAllBtn = document.getElementById('niche-all');
  var nicheClearBtn = document.getElementById('niche-clear');
  if (urlCities.length > 0 && cityEl) {
    Array.from(cityEl.options).forEach(function (opt) { opt.selected = urlCities.indexOf(opt.value) !== -1; });
  }
  if (urlNiches.length > 0 && nicheEl) {
    Array.from(nicheEl.options).forEach(function (opt) { opt.selected = urlNiches.indexOf(opt.value) !== -1; });
  }
  if (!isNaN(urlMax) && urlMax >= 1 && urlMax <= maxLeads && maxEl) {
    maxEl.value = urlMax;
  }

  function setSelectedByIndex(selectEl, indexSet) {
    if (!selectEl) return;
    Array.from(selectEl.options).forEach(function (opt, idx) {
      opt.selected = indexSet.has(idx);
    });
  }

  function setAllSelected(selectEl, selected) {
    if (!selectEl) return;
    Array.from(selectEl.options).forEach(function (opt) {
      opt.selected = selected;
    });
  }

  if (cityTopBtn) {
    cityTopBtn.addEventListener('click', function () {
      var top = new Set(Array.from({ length: Math.min(20, cityEl.options.length) }, function (_, i) { return i; }));
      setSelectedByIndex(cityEl, top);
      showMessage('Selected top 20 cities.', 'info');
    });
  }
  if (cityAllBtn) {
    cityAllBtn.addEventListener('click', function () {
      setAllSelected(cityEl, true);
      showMessage('Selected all cities.', 'info');
    });
  }
  if (cityClearBtn) {
    cityClearBtn.addEventListener('click', function () {
      setAllSelected(cityEl, false);
      showMessage('Cleared city selection.', 'info');
    });
  }
  if (nicheAllBtn) {
    nicheAllBtn.addEventListener('click', function () {
      setAllSelected(nicheEl, true);
      showMessage('Selected all niches.', 'info');
    });
  }
  if (nicheClearBtn) {
    nicheClearBtn.addEventListener('click', function () {
      setAllSelected(nicheEl, false);
      showMessage('Cleared niche selection.', 'info');
    });
  }

  function showMessage(text, type) {
    msg.textContent = text;
    msg.className = type || 'info';
    msg.style.display = 'block';
  }

  function setLoading(loading) {
    btn.disabled = loading;
    btn.textContent = loading ? 'Collecting leads...' : 'Get leads';
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var cityEl = document.getElementById('city');
    var nicheEl = document.getElementById('niche');
    var selectedCities = Array.from(cityEl.selectedOptions).map(function (o) { return o.value; });
    var selectedNiches = Array.from(nicheEl.selectedOptions).map(function (o) { return o.value; });
    var maxLeadsVal = parseInt(document.getElementById('max_leads').value, 10) || 10;
    if (selectedCities.length === 0 || selectedNiches.length === 0) {
      showMessage('Select at least one city and one niche.', 'error');
      return;
    }
    if (maxLeadsVal < 1 || maxLeadsVal > maxLeads) {
      showMessage('Please enter between 1 and ' + String(maxLeads) + ' leads.', 'error');
      return;
    }
    setLoading(true);
    showMessage('Starting...', 'info');
    fetch('/api/collect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        city: selectedCities,
        niche: selectedNiches,
        max_leads: maxLeadsVal
      })
    }).then(function (res) {
      var contentType = res.headers.get('content-type') || '';
      if (contentType.indexOf('text/csv') !== -1) {
        return res.text().then(function (text) {
          var a = document.createElement('a');
          a.href = URL.createObjectURL(new Blob([text], { type: 'text/csv' }));
          a.download = 'leads.csv';
          a.click();
          URL.revokeObjectURL(a.href);
          var count = Math.max(0, text.trim().split('\n').length - 1);
          if (count === 0) {
            showMessage('0 leads found. Check: API key is set in Vercel (GOOGLE_PLACES_API_KEY), Places API is enabled for your key, and try different city/niche. Only businesses with website + email are included.', 'error');
          } else {
            showMessage('Done! ' + count + ' leads. CSV downloaded.', 'success');
          }
          setLoading(false);
        });
      }
      return res.json().then(function (data) {
        if (!res.ok) {
          showMessage(data.error || 'Request failed', 'error');
          setLoading(false);
          return;
        }
        var jobId = data.job_id;
        showMessage('Collecting leads... This may take a few minutes.', 'info');
        function check() {
          fetch('/api/status/' + jobId).then(function (r) { return r.json(); }).then(function (s) {
            if (s.status === 'done') {
              showMessage('Done! ' + s.lead_count + ' leads. Download your CSV below.', 'success');
              msg.innerHTML = 'Done! ' + s.lead_count + ' leads. <a class="download" href="/api/download/' + jobId + '">Download CSV</a>';
              msg.className = 'success';
              setLoading(false);
              return;
            }
            if (s.status === 'error') {
              showMessage('Error: ' + (s.error || 'Unknown'), 'error');
              setLoading(false);
              return;
            }
            setTimeout(check, 2500);
          });
        }
        check();
      });
    }).catch(function (err) {
      showMessage('Network error: ' + err.message, 'error');
      setLoading(false);
    });
  });
})();
"""

from scrape_businesses import (
    COLUMNS,
    CITIES,
    NICHES,
    load_config,
    run_collection_for_cities_niches,
)

app = Flask(__name__)
jobs: dict = {}
MAX_LEADS_WEB = 1000
MAX_LEADS_VERCEL = 1000
VERCEL_MAX_TIME_SECONDS = 290
VERCEL = os.environ.get("VERCEL") == "1"


def _run_job(
    job_id: str,
    cities: list[str],
    niches: list[str],
    max_leads: int,
    api_key: str,
) -> None:
    max_time = None
    try:
        max_time = int(os.environ.get("MAX_RUN_SECONDS", 0)) or None
    except (TypeError, ValueError):
        pass
    try:
        leads = run_collection_for_cities_niches(
            api_key=api_key,
            cities=cities,
            niches=niches,
            max_leads=max_leads,
            extract_emails=True,
            sleep_api=0.2,
            sleep_web=0.1,
            max_time_seconds=max_time,
        )
        jobs[job_id]["status"] = "done"
        jobs[job_id]["leads"] = leads
    except Exception as e:
        logging.exception("Job %s failed", job_id)
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@app.route("/")
def index():
    max_leads = MAX_LEADS_VERCEL if VERCEL else MAX_LEADS_WEB
    return render_template_string(
        INDEX_HTML,
        cities=CITIES,
        niches=NICHES,
        max_leads_web=max_leads,
        is_vercel=VERCEL,
    )


@app.route("/static/leads-form.js")
def leads_form_js():
    return Response(LEADS_FORM_JS.strip(), mimetype="application/javascript; charset=utf-8")


def _get_api_key():
    if VERCEL:
        key = os.environ.get("GOOGLE_PLACES_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key or key == "YOUR_GOOGLE_API_KEY_HERE":
            return None
        return key
    try:
        config = load_config(_root / "config.json")
        return config.get("google_api_key")
    except SystemExit:
        return None


@app.route("/api/collect", methods=["POST"])
def api_collect():
    data = request.get_json() or {}
    raw_city = data.get("city")
    raw_niche = data.get("niche")
    cities = [raw_city] if isinstance(raw_city, str) else (raw_city or [])
    niches = [raw_niche] if isinstance(raw_niche, str) else (raw_niche or [])
    cities = [str(c).strip() for c in cities if c]
    niches = [str(n).strip() for n in niches if n]
    try:
        max_leads = int(data.get("max_leads", 10))
    except (TypeError, ValueError):
        max_leads = 10
    if not cities or not niches:
        return jsonify({"error": "Select at least one city and one niche"}), 400
    max_allowed = MAX_LEADS_VERCEL if VERCEL else MAX_LEADS_WEB
    if max_leads < 1 or max_leads > max_allowed:
        return jsonify({"error": f"Number of leads must be between 1 and {max_allowed}"}), 400
    api_key = _get_api_key()
    if not api_key:
        msg = (
            "Set GOOGLE_PLACES_API_KEY in Vercel project Environment Variables."
            if VERCEL
            else "API key not configured. Add config.json with google_api_key or set GOOGLE_PLACES_API_KEY."
        )
        return jsonify({"error": msg}), 500
    if VERCEL:
        try:
            leads = run_collection_for_cities_niches(
                api_key=api_key,
                cities=cities,
                niches=niches,
                max_leads=max_leads,
                extract_emails=True,
                sleep_api=0.2,
                sleep_web=0.1,
                max_time_seconds=VERCEL_MAX_TIME_SECONDS,
            )
        except Exception as e:
            logging.exception("Collect failed")
            return jsonify({"error": str(e)}), 500
        buf = io.StringIO()
        writer = csv_module.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)
        csv_body = buf.getvalue()
        return Response(
            csv_body.encode("utf-8"),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=leads.csv"},
        )
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "leads": [], "error": None}
    thread = Thread(
        target=_run_job,
        args=(job_id, cities, niches, max_leads, api_key),
    )
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def api_status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    j = jobs[job_id]
    out = {"status": j["status"]}
    if j["status"] == "done":
        out["lead_count"] = len(j["leads"])
    if j["status"] == "error":
        out["error"] = j.get("error", "Unknown error")
    return jsonify(out)


@app.route("/api/download/<job_id>")
def api_download(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    j = jobs[job_id]
    if j["status"] != "done":
        return jsonify({"error": "Job not ready for download"}), 400
    buf = io.StringIO()
    writer = csv_module.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(j["leads"])
    buf.seek(0)
    filename = f"leads_{job_id[:8]}.csv"
    return send_file(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lead Dataset Builder</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=Syne:wght@600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #080810;
      --bg-card: rgba(255,255,255,0.05);
      --bg-card-hover: rgba(255,255,255,0.08);
      --accent: #7C6FCD;
      --accent-bright: #A594F9;
      --accent-cyan: #22D3EE;
      --accent-pink: #F472B6;
      --accent-amber: #FBBF24;
      --accent-glow: rgba(124, 111, 205, 0.4);
      --border: rgba(255,255,255,0.1);
      --border-hover: rgba(165,148,249,0.5);
      --text-primary: #F0EDFF;
      --text-muted: #9CA3B8;
      --ease: cubic-bezier(0.4, 0, 0.2, 1);
    }
    * { box-sizing: border-box; }
    body {
      font-family: 'DM Sans', system-ui, sans-serif;
      margin: 0;
      min-height: 100vh;
      padding: 1.5rem 1rem 2rem;
      background: var(--bg-base);
      color: var(--text-primary);
      position: relative;
      overflow-x: hidden;
    }
    .noise {
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.4;
      z-index: 0;
    }
    .noise svg {
      width: 100%;
      height: 100%;
    }
    .glow-wrap {
      position: fixed;
      top: -400px;
      left: 50%;
      transform: translateX(-50%);
      width: 900px;
      height: 900px;
      border-radius: 50%;
      background: radial-gradient(circle at 50% 40%,
        rgba(124, 111, 205, 0.2) 0%,
        rgba(34, 211, 238, 0.08) 40%,
        rgba(244, 114, 182, 0.06) 60%,
        transparent 75%);
      animation: glowPulse 8s ease-in-out infinite;
      z-index: 0;
    }
    .glow-wrap::after {
      content: '';
      position: absolute;
      bottom: -200px;
      left: 50%;
      transform: translateX(-50%);
      width: 500px;
      height: 400px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(244, 114, 182, 0.12) 0%, transparent 70%);
      pointer-events: none;
    }
    @keyframes glowPulse {
      0%, 100% { opacity: 0.7; }
      50% { opacity: 1; }
    }
    .page-inner {
      position: relative;
      z-index: 1;
      max-width: 560px;
      margin: 0 auto;
    }
    .card {
      background: var(--bg-card);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 2rem 1.75rem;
      box-shadow: 0 0 0 1px rgba(255,255,255,0.04),
                  0 24px 48px -12px rgba(0,0,0,0.5),
                  0 0 80px -20px rgba(124, 111, 205, 0.25),
                  0 0 120px -30px rgba(34, 211, 238, 0.1);
      transition: border-color 0.3s var(--ease), box-shadow 0.3s var(--ease);
      position: relative;
    }
    .card::before {
      content: '';
      position: absolute;
      inset: -1px;
      border-radius: 21px;
      padding: 1px;
      background: linear-gradient(135deg, rgba(124,111,205,0.4), transparent 30%, transparent 70%, rgba(34,211,238,0.2));
      -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask-composite: exclude;
      pointer-events: none;
    }
    .card:hover {
      border-color: rgba(255,255,255,0.15);
      box-shadow: 0 0 0 1px rgba(255,255,255,0.06),
                  0 24px 48px -12px rgba(0,0,0,0.5),
                  0 0 100px -15px rgba(124, 111, 205, 0.35),
                  0 0 140px -25px rgba(244, 114, 182, 0.12);
    }
    .header-row {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 0.5rem;
      animation: fadeSlideUp 0.5s var(--ease) forwards;
    }
    .header-row h1 {
      font-family: 'Syne', sans-serif;
      font-size: 28px;
      font-weight: 700;
      margin: 0;
      background: linear-gradient(135deg, #F0EDFF 0%, #C4B5FD 50%, #A594F9 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      letter-spacing: -0.02em;
    }
    .live-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #86efac;
      padding: 5px 12px;
      border: 1px solid rgba(34, 197, 94, 0.4);
      border-radius: 999px;
      background: rgba(34, 197, 94, 0.12);
      flex-shrink: 0;
      box-shadow: 0 0 20px -4px rgba(34, 197, 94, 0.3);
    }
    .live-badge .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #22c55e;
      box-shadow: 0 0 8px #22c55e;
      animation: blink 1.5s ease-in-out infinite;
    }
    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
    .subtitle {
      font-size: 0.9rem;
      color: var(--text-muted);
      margin: 0 0 1.75rem 0;
      animation: fadeSlideUp 0.5s var(--ease) 0.05s both;
    }
    @keyframes fadeSlideUp {
      from {
        opacity: 0;
        transform: translateY(12px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    .divider {
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--border), rgba(124,111,205,0.3), var(--border), transparent);
      margin: 1.25rem 0;
      border: none;
    }
    .field-group {
      animation: fadeSlideUp 0.5s var(--ease) forwards;
    }
    .field-group.city-section { animation-delay: 0.1s; opacity: 0; }
    .field-group.niche-section { animation-delay: 0.2s; opacity: 0; }
    .field-group.leads-section { animation-delay: 0.3s; opacity: 0; }
    .field-group.btn-section { animation-delay: 0.4s; opacity: 0; }
    .section-label {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
    }
    .section-label::before {
      content: '';
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: var(--accent-bright);
      flex-shrink: 0;
    }
    .field-group.niche-section .section-label::before { background: var(--accent-cyan); }
    .quick-actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.6rem;
      flex-wrap: wrap;
    }
    .quick-btn {
      border: 1px solid rgba(255,255,255,0.18);
      background: rgba(255,255,255,0.06);
      color: var(--text);
      padding: 0.35rem 0.65rem;
      border-radius: 0.55rem;
      font-size: 0.78rem;
      font-weight: 500;
      cursor: pointer;
      transition: transform 0.15s var(--ease), border-color 0.15s var(--ease), background 0.15s var(--ease);
    }
    .quick-btn:hover {
      transform: translateY(-1px);
      border-color: rgba(167, 139, 250, 0.55);
      background: rgba(167, 139, 250, 0.14);
    }
    .field-group.leads-section .section-label::before { background: var(--accent-pink); }
    .section-label::after {
      content: '';
      flex: 1;
      height: 1px;
      background: linear-gradient(90deg, var(--border), transparent);
      max-width: 120px;
    }
    .hint {
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 0.35rem;
      margin-bottom: 1rem;
    }
    select, input[type="number"] {
      width: 100%;
      padding: 0.65rem 0.85rem;
      font-size: 0.95rem;
      font-family: 'DM Sans', system-ui, sans-serif;
      background: rgba(0,0,0,0.35);
      border: 1px solid var(--border);
      border-radius: 12px;
      color: var(--text-primary);
      transition: border-color 0.15s var(--ease), box-shadow 0.15s var(--ease);
    }
    select:hover, input[type="number"]:hover {
      border-color: rgba(255,255,255,0.12);
    }
    select:focus, input[type="number"]:focus {
      outline: none;
      border-color: var(--border-hover);
      box-shadow: 0 0 0 3px var(--accent-glow), 0 0 24px -4px rgba(124, 111, 205, 0.25);
    }
    select[multiple] {
      min-height: 120px;
      padding: 0.5rem;
    }
    select[multiple] option {
      padding: 0.35rem 0.5rem;
      border-radius: 6px;
      transition: background 0.15s var(--ease), border-left 0.15s var(--ease);
    }
    select[multiple] option:hover {
      background: var(--bg-card-hover);
    }
    select[multiple] option:checked {
      background: linear-gradient(90deg, rgba(124, 111, 205, 0.35), rgba(34, 211, 238, 0.15));
    }
    select::-webkit-scrollbar {
      width: 4px;
    }
    select::-webkit-scrollbar-track {
      background: transparent;
    }
    select::-webkit-scrollbar-thumb {
      background: linear-gradient(180deg, var(--accent-bright), var(--accent));
      border-radius: 4px;
    }
    .leads-input-wrap {
      position: relative;
    }
    .leads-input-row {
      display: flex;
      align-items: stretch;
      gap: 0;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: rgba(0,0,0,0.35);
      transition: border-color 0.15s var(--ease), box-shadow 0.15s var(--ease);
    }
    .leads-input-row:focus-within {
      border-color: var(--border-hover);
      box-shadow: 0 0 0 3px var(--accent-glow), 0 0 20px -4px rgba(244, 114, 182, 0.2);
    }
    .leads-input-row input {
      border: none;
      border-radius: 12px 0 0 12px;
      background: transparent;
      flex: 1;
      min-width: 0;
    }
    .leads-input-row input:focus {
      box-shadow: none;
    }
    .leads-step-btn {
      width: 40px;
      flex-shrink: 0;
      border: none;
      background: rgba(255,255,255,0.05);
      color: var(--text-muted);
      font-size: 1.1rem;
      cursor: pointer;
      border-radius: 0 12px 12px 0;
      transition: background 0.15s var(--ease), color 0.15s var(--ease);
    }
    .leads-step-btn:hover {
      background: rgba(124, 111, 205, 0.2);
      color: var(--accent-bright);
    }
    .leads-step-btn:first-of-type {
      border-radius: 0;
      border-left: 1px solid var(--border);
    }
    .leads-step-btn:last-of-type {
      border-radius: 0 12px 12px 0;
    }
    .progress-bar-wrap {
      height: 3px;
      background: var(--border);
      border-radius: 999px;
      margin-top: 0.5rem;
      overflow: hidden;
    }
    .progress-bar-fill {
      height: 100%;
      width: var(--leads-pct, 1%);
      background: linear-gradient(90deg, var(--accent), var(--accent-bright), var(--accent-pink));
      border-radius: 999px;
      transition: width 0.3s var(--ease);
      box-shadow: 0 0 12px -2px var(--accent-glow);
    }
    .max-hint {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 0.4rem;
    }
    #btn {
      width: 100%;
      padding: 0.9rem 1.25rem;
      font-size: 1rem;
      font-weight: 600;
      font-family: 'Syne', sans-serif;
      color: white;
      border: none;
      border-radius: 14px;
      cursor: pointer;
      margin-top: 0.5rem;
      background: linear-gradient(135deg, #7C6FCD 0%, #A594F9 40%, #C4B5FD 70%, #A594F9 100%);
      background-size: 200% 200%;
      box-shadow: 0 4px 24px -4px rgba(124, 111, 205, 0.5), 0 0 40px -10px rgba(244, 114, 182, 0.2);
      transition: transform 0.2s var(--ease), box-shadow 0.2s var(--ease), opacity 0.2s var(--ease), background-position 0.4s var(--ease);
    }
    #btn:hover:not(:disabled) {
      transform: scale(1.02);
      background-position: 100% 50%;
      box-shadow: 0 8px 36px -4px rgba(124, 111, 205, 0.55), 0 0 50px -8px rgba(244, 114, 182, 0.25);
    }
    #btn:active:not(:disabled) {
      transform: scale(0.98);
      transition-duration: 0.1s;
    }
    #btn:disabled {
      cursor: not-allowed;
      opacity: 0.85;
      transform: none;
    }
    #btn:disabled .btn-label { visibility: hidden; }
    #btn:disabled::after {
      content: '';
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      width: 24px;
      height: 8px;
      background: no-repeat center/contain;
      background-image: radial-gradient(circle at 0 50%, white 30%, transparent 30%),
                        radial-gradient(circle at 50% 50%, white 30%, transparent 30%),
                        radial-gradient(circle at 100% 50%, white 30%, transparent 30%);
      animation: dotPulse 0.8s ease-in-out infinite;
    }
    @keyframes dotPulse {
      0%, 100% { opacity: 0.5; }
      50% { opacity: 1; }
    }
    #btn {
      position: relative;
    }
    #message {
      margin-top: 1.25rem;
      padding: 0.85rem 1rem;
      border-radius: 12px;
      font-size: 0.875rem;
      display: none;
      border: 1px solid var(--border);
      animation: fadeSlideUp 0.3s var(--ease);
    }
    #message.info {
      background: linear-gradient(135deg, rgba(124, 111, 205, 0.18), rgba(34, 211, 238, 0.08));
      color: var(--accent-bright);
      border-color: rgba(124, 111, 205, 0.3);
      display: block;
    }
    #message.success {
      background: linear-gradient(135deg, rgba(34, 197, 94, 0.18), rgba(34, 211, 238, 0.06));
      color: #86efac;
      border-color: rgba(34, 197, 94, 0.35);
      display: block;
    }
    #message.error {
      background: linear-gradient(135deg, rgba(239, 68, 68, 0.18), rgba(244, 114, 182, 0.08));
      color: #fca5a5;
      border-color: rgba(239, 68, 68, 0.35);
      display: block;
    }
    a.download {
      display: inline-block;
      margin-top: 0.5rem;
      color: var(--accent-bright);
      text-decoration: none;
      font-weight: 500;
      transition: color 0.15s var(--ease), text-shadow 0.15s var(--ease);
    }
    a.download:hover { text-decoration: underline; color: var(--accent-cyan); text-shadow: 0 0 20px rgba(34, 211, 238, 0.4); }
    @media (max-width: 375px) {
      .card { padding: 1.5rem 1.25rem; }
      .header-row h1 { font-size: 24px; }
    }
  </style>
</head>
<body>
  <div class="noise" aria-hidden="true">
    <svg xmlns="http://www.w3.org/2000/svg">
      <filter id="noise">
        <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" stitchTiles="stitch"/>
        <feColorMatrix type="saturate" values="0"/>
      </filter>
      <rect width="100%" height="100%" filter="url(#noise)"/>
    </svg>
  </div>
  <div class="glow-wrap" aria-hidden="true"></div>
  <div class="page-inner">
    <div class="card">
      <div class="header-row">
        <div>
          <h1>Lead Dataset Builder</h1>
          <p class="subtitle">Build targeted lead lists in seconds.</p>
        </div>
        <span class="live-badge"><span class="dot"></span> LIVE</span>
      </div>
      <form id="form" data-max-leads="{{ max_leads_web | default(1000) | int }}">
        <div class="field-group city-section">
          <label class="section-label" for="city">Cities</label>
          <select id="city" name="city" multiple size="8">
            {% for c in cities %}
            <option value="{{ c | e }}">{{ c | e }}</option>
            {% endfor %}
          </select>
          <div class="quick-actions">
            <button type="button" class="quick-btn" id="city-top-20">Top 20</button>
            <button type="button" class="quick-btn" id="city-all">All cities</button>
            <button type="button" class="quick-btn" id="city-clear">Clear</button>
          </div>
          <p class="hint">Hold Ctrl (Windows) or Cmd (Mac) to select multiple cities.</p>
        </div>
        <hr class="divider">
        <div class="field-group niche-section">
          <label class="section-label" for="niche">Niches</label>
          <select id="niche" name="niche" multiple size="8">
            {% for n in niches %}
            <option value="{{ n | e }}">{{ n | e }}</option>
            {% endfor %}
          </select>
          <div class="quick-actions">
            <button type="button" class="quick-btn" id="niche-all">All niches</button>
            <button type="button" class="quick-btn" id="niche-clear">Clear</button>
          </div>
          <p class="hint">Hold Ctrl (Windows) or Cmd (Mac) to select multiple niches.</p>
        </div>
        <hr class="divider">
        <div class="field-group leads-section">
          <label class="section-label" for="max_leads">How many leads?</label>
          <div class="leads-input-wrap">
            <div class="leads-input-row">
              <input type="number" id="max_leads" name="max_leads" min="1" max="{{ max_leads_web }}" value="10" required>
              <button type="button" class="leads-step-btn" id="leads-minus" aria-label="Decrease">−</button>
              <button type="button" class="leads-step-btn" id="leads-plus" aria-label="Increase">+</button>
            </div>
            <div class="progress-bar-wrap">
              <div class="progress-bar-fill" id="leads-progress"></div>
            </div>
          </div>
          <small class="max-hint">Max {{ max_leads_web }} per run.{% if is_vercel %} (Vercel: runs up to ~5 min; you get all leads collected in that time.){% endif %}</small>
        </div>
        <div class="field-group btn-section">
          <button type="submit" id="btn"><span class="btn-label">Get leads</span></button>
        </div>
      </form>
      <div id="message" role="status"></div>
    </div>
  </div>
  <script>
    (function() {
      var maxEl = document.getElementById('max_leads');
      var progress = document.getElementById('leads-progress');
      var form = document.getElementById('form');
      var maxVal = parseInt(form.getAttribute('data-max-leads'), 10) || 1000;
      function updateProgress() {
        var v = parseInt(maxEl.value, 10) || 0;
        v = Math.min(maxVal, Math.max(1, v));
        progress.style.setProperty('--leads-pct', (v / maxVal * 100) + '%');
      }
      maxEl.addEventListener('input', updateProgress);
      maxEl.addEventListener('change', updateProgress);
      document.getElementById('leads-minus').addEventListener('click', function() {
        var v = parseInt(maxEl.value, 10) || 10;
        maxEl.value = Math.max(1, v - 1);
        updateProgress();
      });
      document.getElementById('leads-plus').addEventListener('click', function() {
        var v = parseInt(maxEl.value, 10) || 10;
        maxEl.value = Math.min(maxVal, v + 1);
        updateProgress();
      });
      updateProgress();
    })();
  </script>
  <script src="/static/leads-form.js"></script>
</body>
</html>
"""
