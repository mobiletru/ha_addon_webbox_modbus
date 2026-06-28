"""Flask server + single-page UI for the full WebBox/SI Modbus panel."""

from __future__ import annotations
import os
from flask import Flask, request, jsonify, Response

from . import core as K
from . import writable as W

app = Flask(__name__)


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify({"host": K.HOST, "unit": K.UNIT, "values": K.read_dashboard()})


@app.route("/api/read")
def api_read():
    try:
        address = int(request.args.get("address", "0"))
        fix = int(request.args.get("fix", "0"))
        unit = int(request.args.get("unit", K.UNIT))
    except (TypeError, ValueError):
        return jsonify({"error": "address, fix, and unit must be integers"}), 400
    dtype = request.args.get("dtype", "U32").upper()
    if not (0 <= address <= 65533):
        return jsonify({"error": f"address {address} out of range "
                        "(must be 0-65533)"}), 400
    if not (0 <= unit <= 247):
        return jsonify({"error": f"unit {unit} out of range (0-247)"}), 400
    if dtype not in ("U16", "S16", "U32", "S32", "U64", "S64"):
        return jsonify({"error": f"unknown data type {dtype}"}), 400
    return jsonify(K.read_generic(address, dtype, fix, unit))


@app.route("/api/writable")
def api_writable():
    return jsonify({k: {"address": v.address, "unit": v.unit, "min": v.vmin,
                        "max": v.vmax, "note": v.note}
                    for k, v in W.WRITABLE.items()})


@app.route("/api/write", methods=["POST"])
def api_write():
    d = request.get_json(force=True)
    if not d.get("param"):
        return jsonify({"error": "no setpoint selected"}), 400
    try:
        value = float(d.get("value"))
    except (TypeError, ValueError):
        return jsonify({"error": "enter a numeric value before writing"}), 400
    return jsonify(K.write_known(d.get("param"), value,
                                 bool(d.get("confirm")),
                                 int(d.get("unit", K.UNIT))))


@app.route("/api/write_raw", methods=["POST"])
def api_write_raw():
    d = request.get_json(force=True)
    try:
        words = [int(x) & 0xFFFF for x in d.get("words", [])]
    except (TypeError, ValueError):
        return jsonify({"error": "words must be a list of integers"}), 400
    if not words:
        return jsonify({"error": "no words to write"}), 400
    return jsonify(K.write_raw(int(d.get("address")), words, d.get("ack", ""),
                               bool(d.get("confirm")), int(d.get("unit", K.UNIT))))


PAGE = r"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>WebBox / Sunny Island Modbus</title>
<style>
 :root{--bg:#12161b;--card:#1a2028;--line:#2a323d;--fg:#e6e9ee;--mut:#8b96a5;
   --acc:#7fd1b9;--warn:#e0a36b;--danger:#d9534f}
 *{box-sizing:border-box}
 body{font-family:'IBM Plex Sans',system-ui,sans-serif;background:var(--bg);
   color:var(--fg);margin:0;padding:1rem;max-width:920px;margin:auto}
 h1{font-size:1.15rem;font-weight:600}
 h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);
   margin:1.4rem 0 .5rem}
 .card{background:var(--card);border:1px solid var(--line);border-radius:10px;
   padding:1rem;margin-bottom:.6rem}
 .grid{display:grid;grid-template-columns:1fr auto auto;gap:.3rem .9rem;
   font-family:'IBM Plex Mono',monospace;font-size:.9rem;align-items:baseline}
 .grid .v{text-align:right;color:var(--acc);font-weight:600}
 .grid .a{text-align:right;color:var(--mut);font-size:.78rem}
 label{font-size:.78rem;color:var(--mut);display:block;margin-bottom:.2rem}
 input,select,button{font:inherit;padding:.45rem .55rem;border-radius:6px;
   border:1px solid var(--line);background:#0e1216;color:var(--fg)}
 .row{display:flex;gap:.5rem;flex-wrap:wrap;align-items:end}
 button{cursor:pointer;background:#222c36;border-color:#37424f}
 button.go{background:#3a2a1c;border-color:#5a4030;color:#f0c89a}
 button.danger{background:#3a1c1c;border-color:#6a2a2a;color:#f0a0a0}
 pre{white-space:pre-wrap;font-family:'IBM Plex Mono',monospace;font-size:.8rem;
   color:#cdd3da;background:#0e1216;border:1px solid var(--line);border-radius:6px;
   padding:.6rem;margin:.5rem 0 0;max-height:240px;overflow:auto}
 .warn{color:var(--warn)} small{color:var(--mut)}
 details summary{cursor:pointer;color:var(--warn);font-size:.85rem}
</style></head><body>
<h1>WebBox / Sunny Island &mdash; <span id=hdr></span></h1>

<h2>Live dashboard</h2>
<div class=card><div class=grid id=dash>loading&hellip;</div></div>

<h2>Register explorer (read any address)</h2>
<div class=card>
 <div class=row>
  <div><label>Address</label><input id=raddr type=number value=30845 style=width:8rem></div>
  <div><label>Type</label><select id=rtype>
    <option>U16</option><option>S16</option><option selected>U32</option>
    <option>S32</option><option>U64</option><option>S64</option></select></div>
  <div><label>FIX (÷10^n)</label><input id=rfix type=number value=0 style=width:5rem></div>
  <div><label>Unit id</label><input id=runit type=number value=23 style=width:5rem></div>
  <button onclick=doRead()>Read</button>
 </div>
 <small>SI parameters live around 47xx-56xx in the manual; addresses vary by
   firmware, so probe here to find what yours exposes.</small>
 <pre id=rout></pre>
</div>

<h2>Guarded setpoint write</h2>
<div class=card>
 <div class=row>
  <div><label>Setpoint</label><select id=wparam></select></div>
  <div><label>Value</label><input id=wval type=number step=0.1 style=width:7rem></div>
  <button onclick=wdry()>Check</button>
  <button class=go onclick=wwrite()>Write &amp; verify</button>
 </div>
 <pre id=wout></pre>
</div>

<details><summary>Advanced: raw register write (disabled unless ack configured)</summary>
<div class=card>
 <div class=row>
  <div><label>Address</label><input id=xaddr type=number style=width:8rem></div>
  <div><label>Words (comma hex/dec)</label><input id=xwords placeholder="0,4950" style=width:11rem></div>
  <div><label>Unit</label><input id=xunit type=number value=23 style=width:5rem></div>
  <div><label>Ack token</label><input id=xack style=width:9rem></div>
  <button class=danger onclick=xwrite()>Raw write</button>
 </div>
 <small>Refused for clamped safety registers. Requires RAW_WRITE_ACK set in
   the add-on config and supplied here. Big-endian words, full block.</small>
 <pre id=xout></pre>
</div></details>

<script>
const J=(u,o)=>fetch(u,o).then(r=>r.json());
async function dash(){
 const d=await J('api/dashboard');
 document.getElementById('hdr').textContent=`unit ${d.unit} @ ${d.host}`;
 const v=d.values||{};let h='';
 for(const k in v){if(k[0]=='_')continue;const r=v[k];
  h+=`<div>${r.label||k}</div><div class=v>${r.value==null?'&mdash;':r.value} ${r.unit||''}</div>`
    +`<div class=a>${r.address}</div>`;}
 document.getElementById('dash').innerHTML=h||'no data';
}
async function doRead(){
 const q=new URLSearchParams({address:raddr.value,dtype:rtype.value,
   fix:rfix.value,unit:runit.value});
 rout.textContent='reading…';
 rout.textContent=JSON.stringify(await J('api/read?'+q),null,2);
}
async function loadW(){
 const d=await J('api/writable');const s=document.getElementById('wparam');
 s.innerHTML='';for(const k in d){const o=document.createElement('option');
  o.value=k;o.textContent=`${k} (${d[k].min}-${d[k].max} ${d[k].unit})`;s.appendChild(o);}
}
async function wsend(confirm){
 wout.textContent='working…';
 wout.textContent=JSON.stringify(await J('api/write',{method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({param:wparam.value,value:parseFloat(wval.value),confirm})}),null,2);
 if(confirm)dash();
}
function wdry(){wsend(false);}
function wwrite(){if(confirm('Write this setpoint to the live inverter?'))wsend(true);}
async function xwrite(){
 if(!confirm('RAW write to a live battery inverter. Are you sure?'))return;
 const words=xwords.value.split(',').map(s=>parseInt(s.trim(),s.trim().match(/[a-f]/i)?16:10));
 xout.textContent='working…';
 xout.textContent=JSON.stringify(await J('api/write_raw',{method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({address:parseInt(xaddr.value),words,unit:parseInt(xunit.value),
   ack:xack.value,confirm:true})}),null,2);
 dash();
}
dash();loadW();setInterval(dash,5000);
</script></body></html>"""


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


def main():
    port = int(os.environ.get("PANEL_PORT", "8100"))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
