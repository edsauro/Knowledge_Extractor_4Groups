import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import experiment

def main():
    raw, _ = experiment.read_source(); messages=experiment.parse(raw)
    data=json.loads((experiment.OUT/"mentions.json").read_text())
    candidates=[m for m in data if m.get("confidence") == "low"][:5] or data[:5]
    stats={"deepseek_calls":0,"input_tokens":0,"output_tokens":0}; results=[]
    prompt=(experiment.HERE/"prompt_mention.md").read_text()
    for m in candidates:
        row={"mention_id":m["mention_id"],"canonical_url":m["canonical_url"],"windows":{}}
        idx=m["message_index"]
        for radius in (4,8,16):
            w=experiment.window(messages,idx,radius)
            text="\n".join(f"[{x['sequential_index']}] {x['timestamp']} — {x['author_raw']}: {x['text']}" for x in w)
            key=f"sensitivity_{m['mention_id']}_{radius}"
            out,_=experiment.call_deepseek(prompt.format(url=m["canonical_url"],anchor=experiment.payload(messages[idx]),window=text),key,stats)
            row["windows"][str(radius)]={k:out.get(k) for k in ("mention_type","context","technical_topic","confidence")}
        results.append(row)
    (experiment.OUT/"sensitivity.json").write_text(experiment.payload(results))
    print(experiment.payload({"mentions_tested":len(results),"calls":stats["deepseek_calls"],"output":"output/sensitivity.json"}))
if __name__ == "__main__": main()
