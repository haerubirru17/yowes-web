import sys, json
sys.path.insert(0, "/opt/yowes")
from countries import list_countries, get_country
total = 0; no_addr = 0; no_state = 0; no_zip = 0
for c in list_countries():
    g = get_country(c)()
    ku = set()
    for s in g.schools:
        ku.update(s.keys())
    ms = [s["name"] for s in g.schools if not (s.get("province") or s.get("state"))]
    mz = [s["name"] for s in g.schools if not (s.get("postcode") or s.get("zip"))]
    na = [s["name"] for s in g.schools if not s.get("address")]
    n = len(g.schools); total += n
    no_state += len(ms); no_zip += len(mz); no_addr += len(na)
    print(f"{c:12} schools={n:2} fields={sorted(ku)} no-state={len(ms)} no-zip={len(mz)}")
print("TOTAL:", total, "| no-address:", no_addr, "| no-state:", no_state, "| no-zip:", no_zip)
