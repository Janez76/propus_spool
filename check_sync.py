import urllib.request, json, http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

data = json.dumps({"email": "admin@propus.ch", "password": "Biel2503!"}).encode()
req = urllib.request.Request("http://192.168.1.4:9010/auth/login", data=data, headers={"Content-Type": "application/json"})
opener.open(req)

req2 = urllib.request.Request("http://192.168.1.4:9010/api/v1/printers/2")
resp2 = opener.open(req2)
printer = json.loads(resp2.read())

print("=== Propus Spool Slots ===")
for s in sorted(printer.get("slots", []), key=lambda x: x["slot_no"]):
    a = s.get("assignment", {}) or {}
    print(f"  Slot {s['slot_no']}: present={a.get('present')}, spool_id={a.get('spool_id')}, external_id={a.get('external_id')}, meta_source={a.get('meta', {}).get('source') if a.get('meta') else None}")

print("\n=== Klipper save_variables ===")
r = urllib.request.urlopen("http://192.168.1.121/printer/objects/query?save_variables", timeout=10)
klipper = json.loads(r.read())
vars = klipper["result"]["status"]["save_variables"]["variables"]
for i in range(4):
    key = f"t{i}__spool_id"
    print(f"  {key} = {vars.get(key)!r}")

print("\n=== Comparison ===")
for i in range(4):
    slot_no = i + 1
    key = f"t{i}__spool_id"
    klipper_val = vars.get(key)
    slot = next((s for s in printer.get("slots", []) if s["slot_no"] == slot_no), None)
    if slot:
        a = slot.get("assignment", {}) or {}
        propus_ext = a.get("external_id", "")
        propus_present = a.get("present", False)
        klipper_id = None if klipper_val in ("", None, 0) else klipper_val
        propus_id = int(propus_ext.split(":")[1]) if propus_ext and ":" in propus_ext else None
        match = "OK" if klipper_id == propus_id else "MISMATCH"
        print(f"  Spule {slot_no}: Klipper={klipper_id}, Propus={propus_id} (present={propus_present}) -> {match}")
    else:
        print(f"  Spule {slot_no}: no slot in Propus!")
