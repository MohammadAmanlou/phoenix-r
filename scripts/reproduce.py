"""Reproduce archived experiments without overwriting snapshots."""
import argparse, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = {'v1': ['repair_audit.py'], 'v2': ['check_theorem.py'], 'v3': ['audit_v3.py'], 'v4': ['dynamic.py', 'stress.py', 'frontier.py', 'text_env.py']}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', choices=['all', *EXPERIMENTS], default='all')
    p.add_argument('--output', type=Path, default=ROOT/'local_runs')
    a=p.parse_args()
    for ver in (EXPERIMENTS if a.version=='all' else [a.version]):
        dst=a.output.resolve()/ver
        dst.mkdir(parents=True, exist_ok=True)
        for f in (ROOT/'research'/ver).glob('*.py'):
            shutil.copy2(f, dst/f.name)
        for name in EXPERIMENTS[ver]:
            subprocess.run([sys.executable,str(dst/name)],cwd=dst,check=True)
if __name__=='__main__': main()
