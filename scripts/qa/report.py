#!/usr/bin/env python3
"""Synthetic browser evidence to standalone HTML and genuine Excel (stdlib only)."""
import argparse
import base64
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import zipfile
from xml.sax.saxutils import escape as xml_escape

def redact(text):
    """Invitation URLs can appear in browser errors; never share their secrets."""
    text=re.sub(r'eyJ[\w-]+\.[\w-]+\.[\w-]+','[redacted token]',text)
    return re.sub(r'(?i)(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])','[redacted invite]',text)


ROOT = Path(__file__).resolve().parents[2]

def workbook(path, sheets):
    """OOXML inline strings: user text, including = formulas, stays literal text."""
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    def col(n):
        value = ''
        while n:
            n, r = divmod(n-1, 26); value = chr(65+r)+value
        return value
    def clean(value):
        return xml_escape(''.join(c for c in str(value) if c in '\n\r\t' or ord(c) >= 32))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(sheets)+1)) + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
        z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + ''.join(f'<sheet name="{clean(name)}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_) in enumerate(sheets,1)) + '</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))+'<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr('xl/styles.xml', '<styleSheet xmlns="'+ns+'"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F6F6B"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="3"><xf/><xf fontId="1" fillId="2" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        for i,(_,rows) in enumerate(sheets,1):
            width=max(map(len,rows),default=1)
            body=''.join(f'<row r="{r}">'+''.join(f'<c r="{col(c)}{r}" s="{1 if r==1 else 2}" t="inlineStr"><is><t xml:space="preserve">{clean(v)}</t></is></c>' for c,v in enumerate(row,1))+'</row>' for r,row in enumerate(rows,1))
            z.writestr(f'xl/worksheets/sheet{i}.xml',f'<worksheet xmlns="{ns}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="{width}" width="30" customWidth="1"/></cols><sheetData>{body}</sheetData><autoFilter ref="A1:{col(width)}{max(1,len(rows))}"/></worksheet>')

def walk(suites):
    for suite in suites:
        yield from suite.get('specs', [])
        yield from walk(suite.get('suites', []))

def safe_attachment(att, out, png=False):
    if 'path' not in att: return None
    p=Path(att['path'])
    if not p.is_absolute(): p=out/p
    p=p.resolve()
    if not p.is_relative_to(out.resolve()) or not p.is_file() or p.stat().st_size>10_000_000: return None
    data=p.read_bytes()
    if png and not data.startswith(b'\x89PNG\r\n\x1a\n'): return None
    return data

def write_report(catalog, payload, out, metadata, inventory):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    scenarios=catalog['scenarios']; errors=[]; pairs={}; rows=[]
    ids=[s['id'] for s in scenarios]
    if len(ids)!=len(set(ids)): errors.append('Duplicate catalog IDs')
    projects=metadata.get('projects',[])
    if not scenarios: errors.append('Empty scenario inventory cannot pass')
    if catalog.get('projects') != projects: errors.append('Catalog and execution project inventories differ')
    if not projects or len(projects)!=len(set(projects)): errors.append('Invalid project inventory')
    known=set(ids)
    for spec in walk((payload or {}).get('suites', [])):
        match=re.match(r'^\[([A-Z]+-\d{3})\]',spec.get('title',''))
        sid=match[1] if match else ''
        for case in spec.get('tests',[]):
            key=(sid,case.get('projectName',''))
            if sid not in known or key[1] not in projects: errors.append('Unexpected result: '+str(key));continue
            if key in pairs: errors.append('Duplicate result: '+str(key));continue
            pairs[key]=case
    for scenario in scenarios:
        for project in projects:
            case=pairs.get((scenario['id'],project)); image='';actions=[]; steps=[]; duration=0
            state='NOT RUN';message='No runtime evidence for this scenario and viewport.'
            if case:
                results=case.get('results',[]);result=results[-1] if results else {}
                duration=sum(r.get('duration',0) for r in results)
                state='PASSED' if len(results)==1 and result.get('status')=='passed' and case.get('expectedStatus','passed')=='passed' else 'FAILED'
                message='Assertions passed.' if state=='PASSED' else 'Failed, skipped, interrupted, unexpected-failure or retried result.'
                if state!='PASSED':
                    failure=(result.get('error') or next(iter(result.get('errors',[])),{})).get('message','')
                    # A short assertion category is useful; raw provider bodies,
                    # stacks and request headers are deliberately excluded.
                    first=re.sub(r'\x1b\[[0-9;]*m','',str(failure)).splitlines()
                    if first:
                        reason=redact(first[0])[:240]
                        message+=' '+reason
                # Do not copy provider diagnostics or error stacks into shareable reports.
                for att in result.get('attachments',[]):
                    if att.get('name')=='outcome':
                        data=safe_attachment(att,out,png=True)
                        if data: image='data:image/png;base64,'+base64.b64encode(data).decode()
                    if att.get('name')=='ui-actions':
                        data=safe_attachment(att,out)
                        if data:
                            try: actions=json.loads(data)
                            except (ValueError,TypeError): errors.append('Malformed actions: '+scenario['id'])
                def step_names(values):
                    for s in values:
                        if s.get('category')=='test.step': yield s.get('title','')
                        yield from step_names(s.get('steps',[]))
                steps=list(step_names(result.get('steps',[])))
                if not image: state='FAILED';message+=' Missing or unsafe screenshot.'
            if state!='PASSED': errors.append(f"{scenario['id']} / {project}: {message}")
            rows.append({'id':scenario['id'],'project':project,'state':state,'message':message,'duration_ms':duration,'image':image,'actions':actions,'steps':steps})
    if (payload or {}).get('errors'): errors.append('Playwright reported a global execution error')
    # Authored controls are covered only by mapped successful scenarios with a recorded click.
    action_rows=[]
    for action in catalog.get('actions',[]):
        hits=[r for r in rows if r['state']=='PASSED' and r['id'] in action['scenarios'] and any(a.get('kind')=='clicked' and a.get('route')==action['route'] and a.get('name')==action['name'] for a in r['actions'])]
        complete={r['project'] for r in hits} == set(projects)
        action_rows.append({**action,'state':'EXERCISED' if complete else 'NOT EXERCISED','evidence':', '.join(sorted({r['id']+'/'+r['project'] for r in hits}))})
    authored={(a['route'],a['name']) for a in action_rows}
    observed={(a.get('route',''),a.get('name','')) for r in rows for a in r['actions'] if a.get('kind')=='observed'}
    for route,name in sorted(observed-authored): action_rows.append({'route':route,'name':name,'scenarios':[],'state':'UNMAPPED CONTROL','evidence':'Discovered in rendered UI; add an explicit scenario/outcome mapping.'})
    missing_actions=sum(a['state']!='EXERCISED' for a in action_rows)
    if missing_actions: errors.append(f'{missing_actions} controls lack mapped passing action evidence across all viewports')
    summary={'ok':not errors,'generated_at':datetime.now(timezone.utc).isoformat(),'metadata':metadata,'expected':len(scenarios)*len(projects),'passed':sum(r['state']=='PASSED' for r in rows),'failed':sum(r['state']=='FAILED' for r in rows),'not_run':sum(r['state']=='NOT RUN' for r in rows),'not_built':len(catalog.get('gaps',[])),'errors':errors,'action_gaps':sum(a['state']!='EXERCISED' for a in action_rows)}
    # Public result JSON intentionally excludes paths, raw errors, session material and image bodies.
    (out/'summary.json').write_text(json.dumps({**summary,'results':[{k:v for k,v in r.items() if k not in ['image','actions']} for r in rows],'actions':action_rows},indent=2)+'\n')
    sheet_scenarios=[['Scenario ID','Feature','Persona','Scenario','Preconditions','Steps','Expected result','Automation','Evidence kind']]+[[s['id'],s['feature'],s['persona'],s['title'],s['preconditions'],'\n'.join(f'{i}. {v}' for i,v in enumerate(s['steps'],1)),s['expected'],s['status'],s['kind']] for s in scenarios]
    sheets=[('Overview',[['Field','Value']]+[[k,str(v)] for k,v in summary.items() if k not in ['errors','metadata']]+[[k,str(v)] for k,v in metadata.items()]),('Browser scenarios',sheet_scenarios),('Browser results',[['Scenario','Viewport','Result','Actual outcome','Duration ms','Observed test steps']]+[[r['id'],r['project'],r['state'],r['message'],r['duration_ms'],'\n'.join(r['steps'])] for r in rows]),('Action coverage',[['Route','Control','Result','Scenario evidence']]+[[a['route'],a['name'],a['state'],a['evidence']] for a in action_rows]),('Regression inventory',[['Suite','Exact test identity','Requirement','Execution evidence']]+inventory),('Future feature gaps',[['Feature','Status','Next work']]+[[g['feature'],g['status'],g['next']] for g in catalog.get('gaps',[])])]
    workbook(out/'ParentPlus-Test-Scenarios.xlsx',sheets)
    e=lambda value:escape(str(value),quote=True)
    cards=[]
    byid={s['id']:s for s in scenarios}
    for row in rows:
        s=byid[row['id']]
        cards.append(f'<details class="scenario" data-state="{e(row["state"])}"><summary><b>{e(row["id"])} · {e(row["project"])}</b> <span class="badge {row["state"].lower().replace(" ","-")}">{e(row["state"])}</span> {e(s["title"])}</summary><p><b>Feature:</b> {e(s["feature"])} · <b>Persona:</b> {e(s["persona"])} · {e(s["kind"])}</p><p><b>Preconditions:</b> {e(s["preconditions"])}</p><ol>'+''.join('<li>'+e(v)+'</li>' for v in s['steps'])+f'</ol><p><b>Expected:</b> {e(s["expected"])}</p><p><b>Actual:</b> {e(row["message"])} ({row["duration_ms"]} ms)</p>'+('<img loading="lazy" alt="Synthetic app outcome '+e(row['id'])+'" src="'+row['image']+'"/>' if row['image'] else '<p>No screenshot available.</p>')+'</details>')
    action_html=''.join('<tr>'+''.join('<td>'+e(a[k])+'</td>' for k in ['route','name','state','evidence'])+'</tr>' for a in action_rows)
    gaps=''.join('<li><b>'+e(g['feature'])+'</b>: '+e(g['status'])+' — '+e(g['next'])+'</li>' for g in catalog.get('gaps',[]))
    metadata_html=''.join('<dt>'+e(k)+'</dt><dd>'+e(v)+'</dd>' for k,v in metadata.items())
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ParentPlus browser quality report</title><style>body{font:16px system-ui;background:#f3f5f1;color:#22303a;max-width:1100px;margin:30px auto;padding:0 18px}h1{color:#1f6f6b}details,section{background:white;border-radius:12px;padding:18px;margin:14px 0}summary{cursor:pointer;line-height:1.8}.badge{font-size:12px;border-radius:8px;padding:5px;background:#fff0c0}.passed{background:#daf0df}.failed,.not-run{background:#ffe0df}img{display:block;max-width:100%;max-height:760px;object-fit:contain;object-position:left top;border:1px solid #ddd}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:9px;border:1px solid #ddd;text-align:left;overflow-wrap:anywhere}dt{font-weight:bold}dd{margin:0 0 9px;overflow-wrap:anywhere}button,input,select{padding:10px;margin:4px}a{color:#1f6f6b}.scroll{overflow:auto}</style><h1>ParentPlus · browser quality report</h1>'''
    html+=f'<p><b>{"PASSED" if summary["ok"] else "ACTION NEEDED"}</b> · {summary["passed"]}/{summary["expected"]} scenario-viewports passed · {summary["failed"]} failed · {summary["not_run"]} not run · {summary["not_built"]} future feature gaps</p><p>Synthetic local testing. This report does not establish live deployment, every possible interaction, or launch readiness. Action coverage is separately reported; a green scenario total does not close action gaps.</p><p><a href="ParentPlus-Test-Scenarios.xlsx">Download Excel scenario register</a></p><section><h2>Run evidence</h2><dl>{metadata_html}</dl></section><section><h2>Scenario results</h2><label>Search <input id="search" type="search" placeholder="Scenario, feature or persona"></label><label>Result <select id="state"><option>ALL</option><option>PASSED</option><option>FAILED</option><option>NOT RUN</option></select></label><button id="expand">Expand visible scenarios</button></section>'+''.join(cards)+f'<section><h2>Action coverage · {summary["action_gaps"]} gaps</h2><p>EXERCISED means a mapped scenario passed and recorded this control action. Unobserved conditional states remain gaps. Visible controls without a mapping are listed explicitly.</p><div class="scroll"><table><tr><th>Route</th><th>Control</th><th>Status</th><th>Evidence</th></tr>{action_html}</table></div></section><section><h2>Product work remaining</h2><ul>{gaps}</ul></section>'
    if errors:html+='<section><h2>Evidence errors</h2><ul>'+''.join('<li>'+e(v)+'</li>' for v in errors)+'</ul></section>'
    html+='''<script>const cards=[...document.querySelectorAll('.scenario')],search=document.getElementById('search'),state=document.getElementById('state');function filter(){cards.forEach(c=>c.hidden=!(c.textContent.toLowerCase().includes(search.value.toLowerCase())&&(state.value==='ALL'||c.dataset.state===state.value)))}search.addEventListener('input',filter);state.addEventListener('change',filter);document.getElementById('expand').onclick=()=>cards.filter(c=>!c.hidden).forEach(c=>c.open=true);</script></html>'''
    (out/'index.html').write_text(html)
    return summary

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    catalog=json.loads((ROOT/'quality/browser-scenarios.json').read_text())
    metadata=json.loads((args.out/'run-metadata.json').read_text())
    try:
        payload=json.loads((args.out/'playwright.json').read_text()) if (args.out/'playwright.json').is_file() else None
    except (OSError,ValueError):
        payload=None
        metadata['execution_error']='Playwright evidence is unreadable or incomplete; scenarios are NOT RUN.'
    inventory=[]
    inv_path=args.out/'inventory.json'
    if inv_path.is_file():
        inv=json.loads(inv_path.read_text());req=json.loads((ROOT/'quality/requirements.json').read_text())
        mapping={t['ref']:r['id'] for r in req['requirements'] for t in r.get('tests',[])}
        for suite,refs in inv.items():
            if isinstance(refs,list): inventory.extend([[suite,ref,mapping.get(ref,''),'Inventory only; see independent quality workflow for executed results.'] for ref in refs])
    summary=write_report(catalog,payload,args.out,metadata,inventory)
    print(f"Browser report: {summary['passed']}/{summary['expected']} passed; {summary['action_gaps']} action gaps; HTML and Excel: {args.out}")
    raise SystemExit(0 if summary['ok'] else 1)

if __name__=='__main__':main()
