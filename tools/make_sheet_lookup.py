#!/usr/bin/env python3
"""Emit a paste-ready decode tab plus the formulas that label each slot in the Sheet.

THE PROBLEM THIS SOLVES. The form deliberately never sends "old" or "new". It cannot: the
page and its config are public, so a rater who viewed source would find the answer and the
blind would be gone. All the Sheet gets is a pair of opaque keys, slot1_key and slot2_key.

So decoding has to happen AFTER collection, somewhere that is not the public page. There
are two good places, and they are complements rather than alternatives:

  1. Locally, from decode_key.json - what analysis.py, decode_responses.py and
     make_report.py already do. Best for the actual analysis and the write-up.
  2. IN THE SHEET, via a private lookup tab - what this script sets up. Best for eyeballing
     a row while approving payment, which is the moment you have the Sheet open anyway and
     do not want to run anything.

Option 2 does not weaken the blind. The lookup lives in the Sheet, which is permissioned to
the team, never in the repo and never served to a rater. It is read-only formulas over rows
that already exist, so it cannot affect what any participant sees or how they are assigned.

    python3 tools/make_sheet_lookup.py            # writes sheet_lookup.tsv + the formulas
"""
import argparse, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.path.join(ROOT, "decode_key.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "sheet_lookup.tsv"))
    a = ap.parse_args()

    keys = json.load(open(a.key))["keys"]
    rows = [("key", "version", "which", "pair", "codeword")]
    for k, v in sorted(keys.items(), key=lambda kv: (kv[1].get("pair") or "", kv[1]["version"])):
        if v["version"] not in ("old", "new"):
            continue
        rows.append((k, v["version"],
                     "RECREATION" if v["version"] == "new" else "ARCHIVE",
                     v.get("pair", ""), v.get("codeword", "")))

    with open(a.out, "w") as f:
        for r in rows:
            f.write("\t".join(r) + "\n")

    print("Wrote %s (%d keys)\n" % (a.out, len(rows) - 1))
    print("=" * 78)
    print("STEP 1  Make a new tab in the responses Sheet called   decode")
    print("=" * 78)
    print("Paste the contents of sheet_lookup.tsv into A1. Tab-separated, so it splits")
    print("into columns on paste. Then RIGHT-CLICK THE TAB > Hide sheet, so nobody reads")
    print("it over your shoulder while you are screen-sharing the responses.")
    print()
    print("=" * 78)
    print("STEP 2  Add two columns at the far right of the responses tab")
    print("=" * 78)
    print("Header them  slot1_is  and  slot2_is,  then put these in the first data row")
    print("and fill down. Replace <S1> and <S2> with the actual column letters of")
    print("slot1_key and slot2_key (they move whenever HEADERS changes, so check).")
    print()
    print('  slot1_is   =IFERROR(VLOOKUP(<S1>2, decode!$A:$C, 3, FALSE), "")')
    print('  slot2_is   =IFERROR(VLOOKUP(<S2>2, decode!$A:$C, 3, FALSE), "")')
    print()
    print("Each row then reads RECREATION or ARCHIVE in plain words, next to the ratings")
    print("that belong to that slot. IFERROR keeps a test row with an unknown key blank")
    print("rather than showing #N/A down the sheet.")
    print()
    print("=" * 78)
    print("STEP 3  Optional, the one that answers 'who won' at a glance")
    print("=" * 78)
    print("Header a third column  picked  and use h2h_choice_key, column <CK>:")
    print()
    print('  picked     =IFERROR(VLOOKUP(<CK>2, decode!$A:$C, 3, FALSE), "")')
    print()
    print("And to check a code word without hunting for it, against s1_codeword <CW1>:")
    print()
    print('  cw1_ok     =IF(<CW1>2="", "", IF(EXACT(LOWER(<CW1>2),')
    print('               LOWER(IFERROR(VLOOKUP(<S1>2, decode!$A:$E, 5, FALSE),""))),')
    print('               "ok", "WRONG"))')
    print()
    print("=" * 78)
    print("A WARNING ABOUT ORDER")
    print("=" * 78)
    print("Slot 1 is NOT always the same version. The form alternates which side a rater")
    print("sees first, so slot1 is the recreation for about half of them and the archive")
    print("for the rest. That is the whole reason these columns are worth adding: reading")
    print("s1_overall as 'the new one' would be wrong roughly half the time.")


if __name__ == "__main__":
    main()
