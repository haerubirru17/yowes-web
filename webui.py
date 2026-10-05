#!/usr/bin/env python3
"""Yowes Web UI — simple form front-end for the Yowes document generator.

FastAPI + single HTML page. Endpoints:
  GET  /            -> form page
  GET  /api/countries
  GET  /api/schools?country=xx
  POST /api/generate -> renders PNGs, returns download URLs
  GET  /files/{name} -> serve generated PNG
"""
import os
import re
import sys
from pathlib import Path

# Where the yowes engine lives (override with YOWES_DIR env var)
YOWES_DIR = Path(os.environ.get("YOWES_DIR", "/home/agentuser/.hermes/cache/scratch/yowes"))
sys.path.insert(0, str(YOWES_DIR))
OUT_DIR = Path(os.environ.get("YOWES_OUTPUT_DIR", YOWES_DIR / "output"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import uvicorn
from pydantic import BaseModel

from countries import get_country, list_countries

app = FastAPI(title="Yowes Web UI")

try:
    from meta_api import router as meta_router
    app.include_router(meta_router)
except Exception as e:
    print(f"[warn] meta_api unavailable, Auto Magic disabled: {e}")

# Allow the GitHub Pages front-end to call this API from the browser
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://haerubirru17.github.io"],
    allow_origin_regex=r"https://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/countries")
def api_countries():
    out = []
    for code in list_countries():
        gen = get_country(code)()
        out.append({
            "code": code,
            "name": gen.get_country_name(),
            "document_types": gen.get_document_types(),
        })
    return out


@app.get("/api/schools")
def api_schools(country: str):
    try:
        gen = get_country(country)()
    except Exception as e:
        raise HTTPException(400, str(e))
    return gen.schools


class GenReq(BaseModel):
    country: str
    first_name: str
    last_name: str
    school_name: str
    position: str
    date_of_birth: str
    gender: str = "Random"
    document_types: list[str] | None = None


@app.post("/api/generate")
def api_generate(req: GenReq):
    try:
        gen = get_country(req.country)()
        school = gen.search_school(req.school_name)
        if school is None:
            raise HTTPException(400, f"Sekolah '{req.school_name}' tidak ditemukan.")
        types = req.document_types or gen.get_document_types()
        gen._current_person_id = f"{req.first_name}_{req.last_name}".lower()
        gen._current_gender = req.gender
        from countries.utils import clear_photo_cache
        clear_photo_cache()
        files = []
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for dtype in types:
            data = gen.generate_document(
                doc_type=dtype, first=req.first_name, last=req.last_name,
                school=school, position=req.position, dob=req.date_of_birth)
            fname = f"{req.country}_{dtype}_{req.first_name.lower()}_{req.last_name.lower()}_{stamp}.png"
            (OUT_DIR / fname).write_bytes(data)
            files.append(fname)
        return JSONResponse({"ok": True, "files": files,
                             "school": school["name"],
                             "school_full": school})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/files/{name}")
def api_file(name: str):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise HTTPException(400, "bad name")
    path = OUT_DIR / name
    if not path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(path, media_type="image/png", filename=name)


PAGE = r"""<!doctype html>
<html lang="id"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Yowes Doc Generator</title>
<style>
:root{--bg:#0a0e17;--panel:#121a2b;--line:#20293d;--text:#e7eaf3;--muted:#8590a8;--acc:#4f8cff;--ok:#34d399;--bad:#f87171}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.6 system-ui,sans-serif;min-height:100vh;
background-image:radial-gradient(900px 500px at 15% -10%,#152140 0%,transparent 55%)}
.wrap{max-width:760px;margin:0 auto;padding:26px 18px 60px}
h1{font-size:20px;display:flex;align-items:center;gap:10px}
.dot{width:10px;height:10px;border-radius:50%;background:linear-gradient(135deg,#4f8cff,#a78bfa);box-shadow:0 0 12px rgba(79,140,255,.8)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin:14px 0}
label{display:block;font-size:12.5px;color:var(--muted);margin:10px 0 4px}
input,select{width:100%;background:#0e1421;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:9px 11px;font-size:14px}
input:focus,select:focus{outline:none;border-color:var(--acc)}
.row{display:flex;gap:12px}.row>div{flex:1}
button{background:linear-gradient(135deg,#4f8cff,#2563eb);color:#fff;border:0;border-radius:9px;padding:11px 20px;font-size:14.5px;font-weight:600;cursor:pointer;width:100%;margin-top:16px}
button:disabled{opacity:.5;cursor:wait}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.chip{border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:12.5px;color:var(--muted);cursor:pointer;user-select:none}
.chip.on{background:rgba(79,140,255,.15);border-color:var(--acc);color:var(--text)}
.msg{margin-top:12px;font-size:13px;border-radius:8px;padding:9px 12px;display:none}
.msg.err{background:rgba(248,113,113,.12);color:var(--bad);display:block}
.msg.ok{background:rgba(52,211,153,.12);color:var(--ok);display:block}
.results{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}
.results img{width:100%;border:1px solid var(--line);border-radius:8px}
.dl{display:block;text-align:center;font-size:12.5px;color:var(--acc);margin-top:5px;text-decoration:none}
.schoolcard{background:#0e1421;border:1px solid var(--line);border-left:3px solid var(--acc);border-radius:8px;padding:11px 13px;margin-top:10px;font-size:13px}
.schoolcard b{color:var(--text)}
.sgrid{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;margin-top:7px;font-size:12.5px}
.sgrid .k{color:var(--muted)}
#schoolinfo{margin-top:0}
footer{color:var(--muted);font-size:12px;text-align:center;margin-top:26px}
</style></head><body><div class="wrap">
<h1><span class="dot"></span>Yowes Doc Generator <small style="color:var(--muted);font-size:12px">· web UI</small></h1>

<div class="card">
  <label>Negara</label><select id="country"><option value="">memuat…</option></select>
  <label>Jenis dokumen (klik untuk pilih/batal)</label><div class="chips" id="doctypes"></div>
  <label>Sekolah (pilih dari daftar)</label><select id="school"><option value="">pilih negara dulu…</option></select>
  <div id="schoolinfo"></div>
  <div class="row">
    <div><label>Nama depan</label><input id="first" placeholder="Budi"></div>
    <div><label>Nama belakang</label><input id="last" placeholder="Santoso"></div>
  </div>
  <div class="row">
    <div><label>Posisi / Jabatan</label><input id="pos" placeholder="Math Teacher"></div>
    <div><label>Tanggal lahir (tampil di kartu)</label><input id="dob" placeholder="12 May 1990"></div>
  </div>
  <label>Gender foto</label>
  <select id="gender"><option>Random</option><option>Male</option><option>Female</option></select>
  <button id="go">⚡ Generate Dokumen</button>
  <div class="msg" id="msg"></div>
</div>

<div class="results" id="results"></div>
<footer>Yowes Web UI · hasil di server: <code>~/.hermes/cache/scratch/yowes/output</code><br>Untuk keperluan fiksi/kreatif/test saja.</footer>
</div>
<script>
let COUNTRIES=[], DOCTYPES=[], selected=new Set();
const $=id=>document.getElementById(id);
async function j(url,opt){const r=await fetch(url,opt);if(!r.ok){let e;try{e=(await r.json()).detail}catch(_){e=r.statusText}throw new Error(e)}return r.json()}
async function init(){
  COUNTRIES=await j('/api/countries');
  $('country').innerHTML='<option value="">— pilih negara —</option>'+COUNTRIES.map(c=>`<option value="${c.code}">${c.name}</option>`).join('');
}
async function pickCountry(){
  const code=$('country').value; selected.clear(); $('doctypes').innerHTML=''; $('results').innerHTML='';
  if(!code){$('school').innerHTML='<option value="">pilih negara dulu…</option>';return}
  const c=COUNTRIES.find(x=>x.code===code);
  DOCTYPES=c.document_types;
  $('doctypes').innerHTML=DOCTYPES.map(d=>`<span class="chip on" data-d="${d}">${d.replaceAll('_',' ')}</span>`).join('')+`<span class="chip" data-d="__all__">pilih semua</span>`;
  document.querySelectorAll('#doctypes .chip').forEach(ch=>ch.onclick=()=>{
    if(ch.dataset.d==='__all__'){const all=[...document.querySelectorAll('#doctypes .chip')].filter(x=>x.dataset.d!=='__all__');
      const on=all[0].classList.contains('on'); all.forEach(x=>x.classList.toggle('on',!on));}
    else ch.classList.toggle('on');
  });
  const schools=await j('/api/schools?country='+code);
  $('school').innerHTML=schools.map(s=>`<option value="${s.name}">${s.name} — ${s.town||s.city||''}</option>`).join('');
  showSchoolInfo();
}
function schoolInfoHTML(s){
  const rows=[['Alamat',s.address],['Kota',s.city||s.town],['Provinsi',s.province||s.state],
    ['Kode pos',s.postcode||s.zip],['Telepon',s.phone],['NPSN',s.npsn],['Website',s.domain]].filter(r=>r[1]);
  return `<div class="schoolcard"><b>🏫 ${s.name}</b><div class="sgrid">${rows.map(r=>`<span class="k">${r[0]}</span><span>${r[1]}</span>`).join('')}</div></div>`;
}
async function showSchoolInfo(){
  const code=$('country').value, name=$('school').value;
  const box=$('schoolinfo');
  if(!code||!name){box.innerHTML='';return}
  const schools=await j('/api/schools?country='+code);
  const s=schools.find(x=>x.name===name);
  box.innerHTML=s?schoolInfoHTML(s):'';
}
$('school').onchange=showSchoolInfo;
$('country').onchange=pickCountry;
$('go').onclick=async()=>{
  const btn=$('go'),msg=$('msg');
  const types=[...document.querySelectorAll('#doctypes .chip.on')].map(x=>x.dataset.d).filter(d=>d!=='__all__');
  if(!$('country').value||!$('school').value||!$('first').value||!$('last').value||!$('pos').value){msg.className='msg err';msg.textContent='Lengkapi dulu: negara, sekolah, nama, posisi.';return}
  btn.disabled=true;msg.className='msg';msg.style.display='none';$('results').innerHTML='';
  try{
    const res=await j('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      country:$('country').value,first_name:$('first').value.trim(),last_name:$('last').value.trim(),
      school_name:$('school').value,position:$('pos').value.trim(),date_of_birth:$('dob').value.trim()||'—',
      gender:$('gender').value,document_types:types.length?types:null})});
    msg.className='msg ok';msg.textContent=`✅ ${res.count} dokumen dibuat · sekolah: ${res.school}`;
    const card=res.school_full?schoolInfoHTML(res.school_full):'';
    $('results').innerHTML=card+res.files.map(f=>`<div><img src="/files/${f}" loading="lazy"><a class="dl" href="/files/${f}" download>⬇ download ${f.split('_')[1].replaceAll('_',' ')}</a></div>`).join('');
  }catch(e){msg.className='msg err';msg.textContent='❌ '+e.message}
  btn.disabled=false;
};
init();
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "18800"))
    ssl_cert = os.environ.get("SSL_CERT")
    ssl_key = os.environ.get("SSL_KEY")
    if ssl_cert and ssl_key:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning",
                    ssl_certfile=ssl_cert, ssl_keyfile=ssl_key)
    else:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
