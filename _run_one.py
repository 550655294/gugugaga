import os, json, sys, io
os.chdir(r"e:\咕咕嘎嘎")

# Fix console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import generate_scripts as g
import time, traceback

g._add_log("=== Start single generation ===")

with g._lock:
    g._st['running'] = True
    g._st['start_time'] = time.time()

try:
    success = g.generate_one()
    print(f"\n{'SUCCESS' if success else 'FAILURE'}")
    
    # Show recent logs
    logs = g._st.get("logs", [])
    print(f"\n--- Logs ({len(logs)}) ---")
    for l in logs[-10:]:
        print(l)
    
    if success:
        eps = g.get_episodes()
        if eps:
            latest = max(eps, key=lambda x: x[0])
            print(f"\n=== Generated: {latest[1]} ===")
            c = g._read(latest[1])
            # Write to file for reading
            outpath = "e:/咕咕嘎嘎/_latest_output.txt"
            with open(outpath, "w", encoding="utf-8") as f:
                f.write(c)
            print(f"Output written to _latest_output.txt ({len(c)} chars)")
    else:
        # Check failure dir
        import glob
        fails = sorted(glob.glob("失败脚本/*.md"), reverse=True)
        if fails:
            print(f"\nLatest failure file: {fails[0]}")
            # Check if this was generated just now
            import datetime
            stat = os.stat(fails[0])
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
            print(f"Modified: {mtime}")
        else:
            print("No failure files found - likely API error")
except Exception as e:
    print(f"Exception: {e}")
    traceback.print_exc()
finally:
    with g._lock:
        g._st['running'] = False
