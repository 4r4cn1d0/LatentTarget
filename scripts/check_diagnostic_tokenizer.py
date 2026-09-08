"""CPU tokenizer and chat template check. Never loads model weights."""
import argparse
import importlib.metadata
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.diagnostic_pilot import read, write_new, validate_packet, digest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    a=p.parse_args()
    packet=read(a.packet);packet_sha=validate_packet(packet)
    a.out_dir.mkdir(parents=True,exist_ok=False)
    from transformers import AutoTokenizer
    cfg=packet["config"]
    tokenizer=AutoTokenizer.from_pretrained(cfg["model"],revision=cfg["revision"])
    counts=[]
    for r in packet["requests"]:
        p=r["prompt"]
        messages=[{"role":"system","content":p["system"]},{"role":"user","content":p["user"]}]
        text=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        # Match the existing provider's tokenizer fallback path exactly.
        ids=tokenizer(text)["input_ids"]
        if len(ids)>cfg["max_input_tokens"]:raise RuntimeError("prompt too long; do not truncate")
        counts.append({"request_id":r["request_id"],"input_tokens":len(ids),"rendered_text_sha256":digest(text),
                       "token_ids_sha256":digest(ids),"rendered_suffix":text[-120:]})
    choices={str(i):tokenizer.encode(str(i),add_special_tokens=False) for i in range(1,4)}
    if len({tuple(v) for v in choices.values()})!=3 or any(tokenizer.decode(v)!=k for k,v in choices.items()):
        raise RuntimeError("choice tokens are ambiguous")
    write_new(a.out_dir/"tokenizer_check.json", {"status":"CPU_TOKENIZER_PATH_VERIFIED_NOT_GPU_PROCESSOR_PATH",
              "packet_sha256":packet_sha,"model":cfg["model"],"revision":cfg["revision"],
              "packages":{k:importlib.metadata.version(k) for k in ("transformers","tokenizers","huggingface_hub","jinja2")},
              "tokenizer_class":type(tokenizer).__name__,"chat_template_sha256":digest(tokenizer.chat_template),
              "choice_token_ids":choices,"minimum_input_tokens":min(r["input_tokens"] for r in counts),
              "maximum_input_tokens":max(r["input_tokens"] for r in counts),"requests":counts,
              "weights_downloaded_by_this_script":False,"model_generations":0,"gpu_processor_path_tested":False})
    print({"requests":len(counts),"min_tokens":min(r["input_tokens"] for r in counts),"max_tokens":max(r["input_tokens"] for r in counts),"choices":choices})


if __name__=="__main__":main()
