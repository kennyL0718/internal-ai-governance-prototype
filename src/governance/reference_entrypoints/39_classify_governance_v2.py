"""Isolated, resumable full-universe binary v2 entry point."""
import argparse
from ai_restrictions.governance_v2 import run

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--stage', choices=['prepare', 'pilot', 'full', 'report'], default='full')
    p.add_argument('--workers', type=int, default=32)
    args = p.parse_args()
    run(args.stage, args.workers)
