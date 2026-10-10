#!/usr/bin/env python3
import hashlib, json, os, re, sys, time, zipfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
CACHE = OUT / "cache"
ZIP = ROOT / "samples/private/DOC-20261009-WA0011.zip"
URL_RE = re.compile(r"https?://(?:www\.)?github\.com/[^\s<>]+", re.I)
MSG_RE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4}) (\d{1,2}:\d{2}) - (.*)$")

def read_source():
    with zipfile.ZipFile(ZIP) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".txt"))
        return z.read(name).decode("utf-8-sig"), name

def parse(text):
    messages = []
    for line in text.splitlines():
        m = MSG_RE.match(line)
        if m:
            date, clock, rest = m.groups()
            author, sep, body = rest.partition(": ")
            messages.append({"timestamp": f"{date} {clock}", "author_raw": author if sep else "", "text": body if sep else rest, "sequential_index": len(messages)})
        elif messages:
            messages[-1]["text"] += "\n" + line
    return messages

def canonical(raw):
    s = raw.rstrip(".,;:!?)]}\"'")
    m = re.match(r"https?://(?:www\.)?github\.com/([^/#?]+/[^/#?]+)", s, re.I)
    if not m: return None
    owner, repo = m.group(1).split("/", 1)
    return f"https://github.com/{owner}/{re.split(r'[/#?]', repo)[0]}"

def found(messages):
    occurrences = []
    by = {}
    for msg in messages:
        for raw in URL_RE.findall(msg["text"]):
            can = canonical(raw)
            if can:
                item = {"canonical_url": can, "original_url": raw, "message_index": msg["sequential_index"]}
                occurrences.append(item); by.setdefault(can, []).append(item)
    return occurrences, by

def select(messages, by):
    ordered = []
    for msg in messages:
        for raw in URL_RE.findall(msg["text"]):
            can = canonical(raw)
            if can and can not in ordered: ordered.append(can)
    chosen = set(ordered[:25])
    return chosen, ordered

def window(messages, idx, radius):
    lo, hi = max(0, idx-radius), min(len(messages), idx+radius+1)
    return messages[lo:hi]

def payload(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)

def call_deepseek(prompt, cache_key, stats):
    path = CACHE / f"{cache_key}.json"
    if path.exists(): return json.loads(path.read_text()), True
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key: raise RuntimeError("DEEPSEEK_API_KEY is required")
    body = {"model": "deepseek-chat", "messages": [{"role":"user", "content": prompt}], "temperature": 0, "response_format": {"type":"json_object"}}
    req = Request("https://api.deepseek.com/chat/completions", data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"})
    with urlopen(req, timeout=120) as response: data = json.loads(response.read())
    usage = data.get("usage", {})
    stats["deepseek_calls"] += 1; stats["input_tokens"] += usage.get("prompt_tokens", 0); stats["output_tokens"] += usage.get("completion_tokens", 0)
    result = json.loads(data["choices"][0]["message"]["content"])
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result, False

def github(can, stats):
    key = hashlib.sha256(can.encode()).hexdigest()[:16]; path = CACHE / f"gh_{key}.json"
    if path.exists(): return json.loads(path.read_text())
    owner, repo = can.rstrip("/").split("/")[-2:]
    headers = {"Accept":"application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"): headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    req = Request(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
    try:
        with urlopen(req, timeout=30) as r: data = json.loads(r.read())
        stats["github_requests"] += 1
        result = {k:data.get(k) for k in ["full_name","name","description","topics","language","stargazers_count","license","default_branch"]}
        result["license"] = (result["license"] or {}).get("spdx_id") if isinstance(result["license"], dict) else result["license"]
        readme_req = Request(f"https://api.github.com/repos/{owner}/{repo}/readme", headers={**headers, "Accept":"application/vnd.github.raw+json"})
        with urlopen(readme_req, timeout=30) as r: result["readme"] = r.read().decode("utf-8", "replace")
        stats["github_requests"] += 1
    except Exception as e:
        result = {"error": str(e), "full_name": f"{owner}/{repo}", "readme": ""}
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2)); return result

def slug(name): return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "repo"

def main():
    start = time.time(); OUT.mkdir(parents=True, exist_ok=True); CACHE.mkdir(exist_ok=True)
    raw, source_name = read_source(); messages = parse(raw); occurrences, by = found(messages); chosen, ordered = select(messages, by)
    expected = []
    for can in ordered[:25]:
        xs = [x for x in occurrences if x["canonical_url"] == can and can in chosen]
        expected.append({"canonical_url":can,"original_urls":sorted({x["original_url"] for x in xs}),"occurrence_count":len(xs),"message_indexes":[x["message_index"] for x in xs]})
    (HERE/"expected_repos.json").write_text(payload(expected))
    stats = {"messages_read":len(messages),"github_urls_found":sum(len(v) for v in by.values()),"repos_unique_in_source":len(by),"sample_repos":len(chosen),"mentions":0,"deepseek_calls":0,"input_tokens":0,"output_tokens":0,"github_requests":0}
    mention_prompt = (HERE/"prompt_mention.md").read_text(); cap_prompt = (HERE/"prompt_capabilities.md").read_text(); mentions=[]; resources={}
    for can in ordered[:25]:
        for occ in [x for x in occurrences if x["canonical_url"] == can]:
            idx=occ["message_index"]; anchor=messages[idx]; w=window(messages,idx,8); textw="\n".join(f"[{m['sequential_index']}] {m['timestamp']} — {m['author_raw']}: {m['text']}" for m in w)
            mid=hashlib.sha256(f"{anchor['author_raw']}|{anchor['timestamp']}|{can}|{idx}".encode()).hexdigest()[:16]
            result,_=call_deepseek(mention_prompt.format(url=can,anchor=payload(anchor),window=textw),"mention_"+mid,stats)
            result.update({"mention_id":mid,"canonical_url":can,"message_index":idx,"timestamp":anchor["timestamp"],"author_raw":result.get("author_raw",anchor["author_raw"])})
            mentions.append(result)
        stats["mentions"] += len([x for x in occurrences if x["canonical_url"] == can])
        gh=github(can,stats); ctx="\n".join(m.get("context","") for m in mentions if m["canonical_url"]==can)
        cap=call_deepseek(cap_prompt.format(metadata=payload({k:v for k,v in gh.items() if k!="readme"}),readme=gh.get("readme","")[:30000],context=ctx),"cap_"+hashlib.sha256(can.encode()).hexdigest()[:16],stats)[0]
        name=gh.get("name") or can.rsplit("/",1)[-1]; resources[can]={"name":name,"url":can,"what_it_does":cap.get("what_it_does",""),"capabilities":cap.get("capabilities",[]),"github":gh,"mentions":[m for m in mentions if m["canonical_url"]==can]}
    (OUT/"mentions.json").write_text(payload(mentions)); (OUT/"resources.json").write_text(payload(list(resources.values())))
    for r in resources.values():
        g=r["github"]; lines=["---",f"name: {r['name']}",f"url: {r['url']}","kind: github_repo",f"language: {g.get('language') or ''}",f"stars: {g.get('stargazers_count') if g.get('stargazers_count') is not None else ''}","capabilities:"]+[f"  - {x}" for x in r["capabilities"]]+["---",f"\n# {r['name']}","\n## What it does",r["what_it_does"],"\n## Capabilities"]+[f"- {x}" for x in r["capabilities"]]+["\n## Mentions"]
        for m in r["mentions"]: lines += [f"\n### {m.get('timestamp','').split()[0]} — {m.get('author_raw','')}",f"**{m.get('author_raw','')}**",f"\nType: {m.get('mention_type','other')}",f"Confidence: {m.get('confidence','low')}","\n"+m.get("context","")]
        lines += ["\n## Human review","\n<!-- notas humanas podem ser escritas abaixo -->\n"]
        (OUT/"resources"/(slug(r["name"])+".md")).write_text("\n".join(lines))
    stats["duration_seconds"]=round(time.time()-start,2); stats["estimated_cost_usd"]=round(stats["input_tokens"]*0.00000015+stats["output_tokens"]*0.0000006,6); (OUT/"run.json").write_text(payload(stats))
    print(payload(stats))

if __name__ == "__main__": main()
