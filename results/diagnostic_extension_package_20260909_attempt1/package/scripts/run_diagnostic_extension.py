"""Verify or execute the remaining fixed bank choices, once per request."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.diagnostic_pilot import verify_package,read
from src.diagnostic_extension import validate_extension,collect_extension


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true');p.add_argument('--mode',choices=('mock','hf'),default='mock')
    p.add_argument('--approval',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args();verify_package(ROOT)
    packet=read(ROOT/'extension_packet.json');pilot=read(ROOT/'packet.json')
    sha=validate_extension(packet,pilot)
    print(json.dumps({'status':'VERIFIED','packet_sha256':sha,'new_requests':660}),flush=True)
    if a.execute:
        if a.output is None or a.output.resolve().is_relative_to(ROOT):raise ValueError('external output directory required')
        result=collect_extension(packet,pilot,a.output,a.mode,read(a.approval) if a.approval else None)
        print(json.dumps({k:v for k,v in result.items() if k!='response_hashes'}))
