"""Check every new prompt on CPU without downloading model weights."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.diagnostic_pilot import read, write_new, digest
from src.presentation_diagnostic import validate

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    packet = read(a.package / 'presentation_packet.json')
    pilot = read(a.package / 'packet.json')
    sha = validate(packet, pilot)
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(pilot['config']['model'], revision=pilot['config']['revision'])
    counts = []
    for row in packet['requests']:
        prompt = row['prompt']
        text = tokenizer.apply_chat_template([dict(role='system', content=prompt['system']),
                                             dict(role='user', content=prompt['user'])],
                                            tokenize=False, add_generation_prompt=True, enable_thinking=False)
        ids = tokenizer(text)['input_ids']
        if len(ids) > 12000:
            raise RuntimeError('input exceeds bound; no truncation')
        counts.append(dict(request_id=row['request_id'], layout=row['layout'], kind=row['kind'],
                           input_tokens=len(ids), token_ids_sha256=digest(ids)))
    result = dict(status='CPU_TOKENIZER_VERIFIED_NOT_GPU_PROCESSOR', packet_sha256=sha,
                  minimum=min(r['input_tokens'] for r in counts), maximum=max(r['input_tokens'] for r in counts),
                  requests=counts, model_generations=0, model_weights_loaded=False,
                  choice_tokens={d: tokenizer.encode(d, add_special_tokens=False) for d in ('1', '2', '3')})
    write_new(a.output, result)
    print({k: v for k, v in result.items() if k != 'requests'})
