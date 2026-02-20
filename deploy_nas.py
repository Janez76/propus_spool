import paramiko
import time

NAS_HOST = "192.168.1.4"
NAS_USER = "Janez"
NAS_PASS = "Biel2503!"
SRC_DIR = "/volume1/docker/propus_spool_src"

def run(ssh, cmd, timeout=300):
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    rc = stdout.channel.recv_exit_status()
    if out.strip():
        print(out[-2000:] if len(out) > 2000 else out)
    if err.strip():
        print(f"STDERR: {err[-1000:]}")
    print(f"Exit: {rc}")
    return rc, out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NAS_HOST, username=NAS_USER, password=NAS_PASS)

run(ssh, f"cd {SRC_DIR} && git pull")
run(ssh, f"cd {SRC_DIR} && docker build -t propus-spool:latest .", timeout=600)
run(ssh, "cd /volume1/docker/fila-propus-clean && docker compose up -d fila-propus-app", timeout=120)

time.sleep(5)
run(ssh, "docker logs fila-propus-app --tail 15")

ssh.close()
print("\nDone!")
