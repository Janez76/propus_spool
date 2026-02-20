import paramiko, sys, base64
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.4', username='Janez', password='Biel2503!')

script = """\
import httpx, asyncio, re

async def main():
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        # Get the dashboard JS
        r = await c.get("http://fila-propus-app:8000/_astro/index.astro_astro_type_script_index_0_lang.BzoyLu00.js")
        js = r.text
        
        # Check imports
        imports = re.findall(r'from"([^"]+)"', js)
        print("Imports:")
        for imp in imports:
            print("  %s" % imp)
            # Check if each import resolves
            if imp.startswith("./"):
                url = "http://fila-propus-app:8000/_astro/" + imp[2:]
                ir = await c.get(url)
                print("    Status: %s, %s bytes" % (ir.status_code, len(ir.content)))
        
        # Check if the JS has the error handler
        has_error = "Dashboard Error" in js or "Dashboard init failed" in js
        print("\\nHas error handler: %s" % has_error)
        
        # Check if loadDashboardData exists
        has_load = "loadDashboardData" in js or "dashboard/stats" in js
        print("Has loadDashboardData: %s" % has_load)
        
        # Check first 200 chars
        print("\\nJS start: %s" % repr(js[:200]))
        
        # Check for syntax issues - look for common problems
        print("\\nJS length: %s" % len(js))
        
        # Now check the Layout JS too
        r2 = await c.get("http://fila-propus-app:8000/_astro/Layout.astro_astro_type_script_index_0_lang.7u840cts.js")
        js2 = r2.text
        imports2 = re.findall(r'from"([^"]+)"', js2)
        print("\\nLayout imports:")
        for imp in imports2:
            print("  %s" % imp)
            if imp.startswith("./"):
                url = "http://fila-propus-app:8000/_astro/" + imp[2:]
                ir = await c.get(url)
                print("    Status: %s" % ir.status_code)
        
        has_checkauth = "checkAuth" in js2 or "/api/v1/me" in js2
        print("Layout has checkAuth: %s" % has_checkauth)
        
        has_syncLang = "syncLangFromUser" in js2 or "reload" in js2
        print("Layout has syncLang/reload: %s" % has_syncLang)

asyncio.run(main())
"""
encoded = base64.b64encode(script.encode()).decode()
cmd = "docker exec fila-propus-app python -c \"import base64; exec(base64.b64decode('%s').decode())\"" % encoded
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
if out.strip():
    print(out.strip())
if err.strip():
    for line in err.strip().split('\n')[-5:]:
        print('ERR:', line)

ssh.close()
