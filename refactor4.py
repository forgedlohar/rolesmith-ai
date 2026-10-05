import sys

path = "src/rolesmith/server.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("autopilot.pipeline", "rolesmith.pipeline.pipeline")
content = content.replace("autopilot.store", "rolesmith.pipeline.store")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
