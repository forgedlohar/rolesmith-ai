import os
import re

def main():
    path = "tests/test_rolesmith.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    content = content.replace("autopilot.models", "rolesmith.pipeline.models")
    content = content.replace("autopilot.rating", "rolesmith.pipeline.rating")
    content = content.replace("autopilot.tailor", "rolesmith.pipeline.tailor")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    main()
