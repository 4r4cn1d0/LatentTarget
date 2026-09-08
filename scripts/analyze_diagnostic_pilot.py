"""Analyze all planned pilot cells and every precomputed reference policy."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.diagnostic_pilot import read,write_new,file_sha
from src.diagnostic_analysis import summarize


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package-dir",type=Path,required=True)
    p.add_argument("--responses-dir",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    a=p.parse_args()
    manifest=read(a.package_dir/"manifest.json")
    for f,h in manifest["files"].items():
        if not (a.package_dir/f).resolve().is_relative_to(a.package_dir.resolve()) or file_sha(a.package_dir/f)!=h:
            raise ValueError("pilot package changed")
    packet=read(a.package_dir/"package/packet.json");analyst=read(a.package_dir/"analyst_key.json")
    paths=sorted(a.responses_dir.glob("*.response.json"));raw=[read(p) for p in paths]
    run=read(a.responses_dir/"run.json")
    if run["packet_sha256"]!=analyst["packet_sha256"]:raise ValueError("run identity mismatch")
    for r in raw:
        if any(r.get(k)!=v for k,v in run.items()):raise ValueError("mixed provider or run identity")
    result=summarize(packet,analyst,raw)
    baselines={name:summarize(packet,analyst,rows) for name,rows in read(a.package_dir/"baseline_responses.json").items()}
    a.out_dir.mkdir(parents=True,exist_ok=False)
    write_new(a.out_dir/"summary.json",dict(result,run_identity=run,baselines=baselines))
    lines=["# Diagnostic collection report","",f"Source: {run['mode']}; model: {run['model']}.",
           "MOCK OUTPUTS ARE NOT RESEARCH RESULTS." if run["mode"]=="mock" else "Three bundles only. These data do not support confirmatory inference.",
           f"Valid choices: {result['valid_choices']}/60. Missing and invalid cells stay in worst case bounds.",
           "No simulated future choice is described as an observed focal interaction.","",
           "| Source | BIND | TRANSFER | NEAR | No history familiar | No history composite | Random |",
           "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name,res in [(run["model"],result),*baselines.items()]:
        lines.append("| "+name+" | "+" | ".join(f"{lo:.3f}" if abs(lo-hi)<1e-12 else f"[{lo:.3f}, {hi:.3f}]" for lo,hi in zip(res["mean_lower"],res["mean_upper"]))+" |")
    lines += ["","All reference policies are retained. Annotated feature reward, static belief and the oracle receive privileged frame annotations.",
              "These normalized contrasts are not success rates. The RANDOM contrast uses pseudo type geometry only.",""]
    for bid in packet["provenance"]["selected_bundles"]:
        lines += [f"## {bid}",""]
        for r in result["requests"]:
            if r["request_id"].split("/")[0]!=bid:continue
            lines += [f"### {r['request_id']}","",f"Raw output: {r['raw_response']!r}. Status: {r['status']}.",
                      f"Message: {r['selected_message']}",f"Registered vector: {r['registered_vector']}. Simulator expected P(A): {r['simulator_expected_p_a']}.",""]
    (a.out_dir/"PILOT_COLLECTION_REPORT.md").write_text("\n".join(lines))
    write_new(a.out_dir/"manifest.json",{"inputs":{str(p.resolve()):file_sha(p) for p in [*paths,a.responses_dir/"run.json",a.package_dir/"manifest.json",Path(__file__),ROOT/"src/diagnostic_analysis.py"]},
              "outputs":{p.name:file_sha(p) for p in a.out_dir.iterdir() if p.is_file()},"source_mode":run["mode"]})
    print({"mode":run["mode"],"valid":result["valid_choices"],"n":3,"confirmatory":False})


if __name__=="__main__":main()
