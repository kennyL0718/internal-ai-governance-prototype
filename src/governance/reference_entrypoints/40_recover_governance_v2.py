"""Finite, audited recovery of v2 response exceptions after the full run."""
import argparse
from ai_restrictions import governance_v2 as v
from ai_restrictions.governance_v2_recovery import offline_recover,retry_recovery

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--retry',action='store_true')
    p.add_argument('--limit',type=int)
    p.add_argument('--workers',type=int,default=16)
    p.add_argument('--round',type=int,choices=[1,2],default=1)
    args=p.parse_args()
    offline_recover()
    if args.retry:
        states,meta=v.prepare()
        retry_recovery(states,args.workers,args.limit,args.round)
