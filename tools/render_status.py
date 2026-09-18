#!/usr/bin/env python3
"""What audio exists, what is missing, and whether a cache from another machine is complete.

    python tools/render_status.py                       # what is done, what is left
    python tools/render_status.py --verify              # check every index entry resolves
    python tools/render_status.py --manifest work.json  # emit the outstanding list

WHY THIS EXISTS
---------------
The render is portable across machines, and it is worth understanding why: a clip's filename IS
the hash of what it says.

    filename = sha256(text + locale + voice + engine + engine_version)

So the cache is content-addressed. Two machines rendering different locales produce disjoint
files that merge by copying, with no coordination and no possibility of a conflict - if two
machines DID render the same span they would produce the same filename, and one would simply
overwrite the other with identical content.

That makes the GPU handoff trivial: a collaborator renders whatever is missing, ships
audio_cache/wav/, and you copy it in. No merge step, no resume protocol, no shared state. This
tool just tells you what is outstanding and confirms afterwards that nothing is.
"""

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

SEP = "␟"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default=None)
    ap.add_argument("--engine", default="parler",
                    help="which engine's keys to check: parler (production) or kokoro")
    ap.add_argument("--voice", default="default")
    ap.add_argument("--verify", action="store_true",
                    help="confirm every index entry points at a file that exists")
    ap.add_argument("--manifest", default=None,
                    help="write the outstanding spans to a JSON file")
    ap.add_argument("--cache", default=None,
                    help="cache to inspect; defaults to audio_cache/wav, or "
                         "$VOICEAGENT_AUDIO_CACHE/wav if set")
    args = ap.parse_args()

    from engine import Content                                    # noqa: PLC0415
    from engine import prerender as pre                           # noqa: PLC0415

    content = Content(args.pack)
    cls = pre.RENDERERS[args.engine]
    name, version = cls.name, cls.version

    WAV = pathlib.Path(args.cache) / "wav" if args.cache else pre.WAV_CACHE
    WAV.mkdir(parents=True, exist_ok=True)

    # The same plan the renderer works from - not a second implementation of it. If these two
    # ever disagreed, this tool would cheerfully report a complete render the server cannot
    # serve, which is the one failure it exists to catch.
    wanted = pre.plan(content, engine=name, version=version, voice=args.voice)
    todo = pre.outstanding(wanted, WAV)
    done = {k: v for k, v in wanted.items() if k not in todo}

    print(f"\n  pack   {content.pack_name} @ {content.content_hash} ({content.provenance})")
    print(f"  engine {name} v{version}   voice {args.voice}")
    print(f"  cache  {WAV}\n")
    print(f"  {'locale':8} {'needed':>7} {'rendered':>9} {'missing':>8}")
    by_locale = collections.Counter(loc for loc, _ in wanted.values())
    done_locale = collections.Counter(loc for loc, _ in done.values())
    for loc in content.locales:
        need, got = by_locale.get(loc, 0), done_locale.get(loc, 0)
        flag = "" if need == got else "   <-"
        print(f"  {loc:8} {need:>7} {got:>9} {need - got:>8}{flag}")
    pct = len(done) / len(wanted) * 100 if wanted else 100
    print(f"\n  {len(done)}/{len(wanted)} spans rendered ({pct:.0f}%)")

    index_path = WAV / pre.INDEX_NAME
    if index_path.exists():
        doc = pre.load_index(WAV)
        print(f"  index: {doc.get('engine')} v{doc.get('engine_version')} · "
              f"{len(doc.get('spans', {}))} entries")
        if doc.get("engine") != name:
            print(f"  NOTE  the index was written by {doc.get('engine')!r}, not {name!r}. "
                  f"The server plays whatever the index points at, so it is still serving "
                  f"{doc.get('engine')} audio until a {name} run completes and rewrites it.")
    else:
        print("  index: none yet - written when a render finishes a locale set")

    if args.verify and index_path.exists():
        doc = pre.load_index(WAV)
        broken = [k for k, f in doc.get("spans", {}).items() if not (WAV / f).exists()]
        print(f"\n  verify: {len(doc.get('spans', {})) - len(broken)} entries resolve, "
              f"{len(broken)} broken")
        for k in broken[:5]:
            print(f"    MISSING {k.split(SEP)[-1][:56]}")

    if args.manifest:
        out = [{"locale": loc, "text": text, "key": k} for k, (loc, text) in sorted(
            todo.items(), key=lambda kv: kv[1][0])]
        pathlib.Path(args.manifest).write_text(
            json.dumps({"pack": content.pack_name, "content_hash": content.content_hash,
                        "engine": name, "engine_version": version, "voice": args.voice,
                        "outstanding": out}, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"\n  outstanding -> {args.manifest} ({len(out)} spans)")

    if todo:
        locales = sorted({loc for loc, _ in todo.values()})
        print(f"\n  to finish:  python tools/prerender_audio.py --engine {args.engine} "
              f"--locales {' '.join(locales)}")
        print("  (already-rendered clips are skipped, so this is safe to re-run any time)")
    else:
        print("\n  complete - restart apps/server.py to pick it up")
    return 0


if __name__ == "__main__":
    sys.exit(main())
