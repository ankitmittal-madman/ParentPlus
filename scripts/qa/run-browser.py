#!/usr/bin/env python3
"""Run a fresh, local-only browser evidence session; preserve previous reports."""
from datetime import datetime, timezone
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from report import redact

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--not-run',action='store_true',help='produce an explicit NOT RUN report after setup failure')
parser.add_argument('--grep',help='diagnostic subset only; full report still marks missing scenarios NOT RUN')
args=parser.parse_args()
OUT=ROOT/'test-results/qa'/('run-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:6])
OUT.mkdir(parents=True,exist_ok=False)
module=importlib.util.spec_from_file_location('quality',ROOT/'scripts/quality/quality_gate.py')
quality=importlib.util.module_from_spec(module);module.loader.exec_module(quality)
metadata={'projects':['desktop','mobile'],'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_fingerprint':quality.source_fingerprint(ROOT),'dirty_checkout':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),'environment':'Real local Supabase; synthetic .test data; dummy OTP; no hosted requests','started_at':datetime.now(timezone.utc).isoformat(),'github_run':os.environ.get('GITHUB_RUN_ID','local')}
(OUT/'run-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
# Raw files stay private and are excluded from CI upload. Only the sanitised reports are shared.
os.chmod(OUT,0o700)
env=dict(os.environ,PARENTPLUS_QA_OUTPUT=str(OUT))
result=1
try:
    if not args.not_run:
        inventory=subprocess.run([sys.executable,'scripts/quality/quality_gate.py','inventory'],cwd=ROOT,capture_output=True,text=True)
        if inventory.returncode == 0:
            (OUT/'inventory.json').write_text(inventory.stdout)
            process=subprocess.Popen([sys.executable,'scripts/dev/founder-app.py','--qa']+(['--grep',args.grep] if args.grep else []),cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            for line in process.stdout:
                print(redact(line),end='',flush=True)
            result=process.wait()
        else:
            print('Inventory setup failed; scenarios will be reported NOT RUN. No raw diagnostics uploaded.',flush=True)
finally:
    report=subprocess.run([sys.executable,'scripts/qa/report.py','--out',str(OUT)],cwd=ROOT).returncode
    (ROOT/'test-results/qa/latest-run.txt').write_text(str(OUT)+'\n')
    print('Founder report:',OUT/'index.html',flush=True)
raise SystemExit(result or report)
