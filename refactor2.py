import os
import re

def main():
    base_dir = "src/rolesmith"
    for root, _, files in os.walk(base_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Replace job-apply-mcp with rolesmith
            content = content.replace("job-apply-mcp", "rolesmith")
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

if __name__ == "__main__":
    main()
