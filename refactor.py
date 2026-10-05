import os
import re

def main():
    base_dir = "tests"
    for root, _, files in os.walk(base_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            content = re.sub(r'^(import autopilot)', r'import rolesmith.pipeline', content, flags=re.MULTILINE)
            content = re.sub(r'^(from autopilot\.)', r'from rolesmith.pipeline.', content, flags=re.MULTILINE)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

if __name__ == "__main__":
    main()
