import base64

with open(".env") as f:
    lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

env_vars = {}
for line in lines:
    if "=" in line:
        k, v = line.split("=", 1)
        env_vars[k.strip()] = v.strip()

# Correction : Kestra tourne dans Docker, il doit utiliser host.docker.internal
if "DATABASE_URL" in env_vars:
    env_vars["DATABASE_URL"] = env_vars["DATABASE_URL"].replace("localhost", "host.docker.internal")

print("Ajoute ces lignes dans le bloc 'environment:' du service kestra :\n")
for key in ["DATABASE_URL", "GOOGLE_MAPS_API_KEY", "SLACK_BOT_TOKEN", "SLACK_CHANNEL", "BONUS_RATE", "WELLNESS_MIN_ACTIVITIES", "WELLNESS_DAYS"]:
    if key in env_vars:
        encoded = base64.b64encode(env_vars[key].encode()).decode()
        print(f"      SECRET_{key}: {encoded}")