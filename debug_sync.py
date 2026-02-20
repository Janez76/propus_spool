import urllib.request, json, http.cookiejar, time

def get_klipper_vars():
    r = urllib.request.urlopen("http://192.168.1.121/printer/objects/query?save_variables", timeout=10)
    data = json.loads(r.read())
    return data["result"]["status"]["save_variables"]["variables"]

def get_propus_slots():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    data = json.dumps({"email": "admin@propus.ch", "password": "Biel2503!"}).encode()
    req = urllib.request.Request("http://192.168.1.4:9010/auth/login", data=data, headers={"Content-Type": "application/json"})
    opener.open(req)
    req2 = urllib.request.Request("http://192.168.1.4:9010/api/v1/printers/2")
    resp2 = opener.open(req2)
    printer = json.loads(resp2.read())
    return printer.get("slots", [])

print("=== STEP 1: Current state ===")
vars = get_klipper_vars()
slots = get_propus_slots()
for i in range(4):
    kv = vars.get(f"t{i}__spool_id")
    slot = next((s for s in slots if s["slot_no"] == i+1), None)
    a = (slot.get("assignment") or {}) if slot else {}
    print(f"  Spule {i+1}: Klipper t{i}__spool_id={kv!r}, Propus spool_id={a.get('spool_id')}, ext={a.get('external_id')}, present={a.get('present')}, source={a.get('meta',{}).get('source') if a.get('meta') else None}")

print("\n=== STEP 2: Setting t2__spool_id=1 via Moonraker (simulating Mainsail assign to T2) ===")
gcode = "SAVE_VARIABLE VARIABLE=t2__spool_id VALUE=1"
req = urllib.request.Request(
    "http://192.168.1.121/printer/gcode/script",
    data=json.dumps({"script": gcode}).encode(),
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req, timeout=10)
print(f"  Moonraker response: {resp.status}")

print("\n=== STEP 3: Verify Klipper immediately ===")
vars2 = get_klipper_vars()
print(f"  t2__spool_id = {vars2.get('t2__spool_id')!r}")

print("\n=== STEP 4: Waiting 15 seconds for Propus poll... ===")
time.sleep(15)

print("\n=== STEP 5: Check Propus after poll ===")
slots2 = get_propus_slots()
slot3 = next((s for s in slots2 if s["slot_no"] == 3), None)
if slot3:
    a = slot3.get("assignment") or {}
    print(f"  Spule 3: spool_id={a.get('spool_id')}, ext={a.get('external_id')}, present={a.get('present')}, source={a.get('meta',{}).get('source') if a.get('meta') else None}")
else:
    print("  Spule 3: NOT FOUND in Propus!")

print("\n=== STEP 6: Check container logs ===")
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.4", username="Janez", password="Biel2503!")
stdin, stdout, stderr = ssh.exec_command("docker logs fila-propus-app --tail 30 2>&1 | grep -i 'klipper\\|slot\\|spool_inserted\\|error'", timeout=15)
logs = stdout.read().decode()
print(logs[-2000:] if len(logs) > 2000 else logs)
ssh.close()

print("\n=== STEP 7: Cleanup - reset t2__spool_id back to empty ===")
gcode2 = 'SAVE_VARIABLE VARIABLE=t2__spool_id VALUE=\\\"\\\"'
req2 = urllib.request.Request(
    "http://192.168.1.121/printer/gcode/script",
    data=json.dumps({"script": gcode2}).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    resp2 = urllib.request.urlopen(req2, timeout=10)
    print(f"  Reset response: {resp2.status}")
except Exception as e:
    print(f"  Reset failed: {e}")
