#!/usr/bin/env python3
from pathlib import Path

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#111827" />
      <stop offset="100%" stop-color="#1f2937" />
    </linearGradient>
    <linearGradient id="accentGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3b82f6" />
      <stop offset="100%" stop-color="#06b6d4" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="400" height="400" rx="40" fill="url(#bgGradient)" />

  <!-- Outer Tech Circle -->
  <circle cx="200" cy="180" r="110" fill="none" stroke="#374151" stroke-width="2" stroke-dasharray="10 10" />
  
  <!-- AI Nodes -->
  <circle cx="90" cy="180" r="4" fill="#60a5fa" />
  <circle cx="310" cy="180" r="4" fill="#60a5fa" />
  <circle cx="200" cy="70" r="4" fill="#60a5fa" />
  <circle cx="200" cy="290" r="4" fill="#60a5fa" />

  <!-- Tech Connections -->
  <path d="M 90 180 L 140 180 M 310 180 L 260 180 M 200 70 L 200 120 M 200 290 L 200 240" stroke="#374151" stroke-width="2" />

  <!-- Hammer / Anvil Shape -->
  <g transform="translate(140, 120)" filter="url(#glow)">
    <!-- Anvil Base -->
    <path d="M 10 110 L 110 110 L 90 90 L 30 90 Z" fill="#94a3b8" />
    <!-- Anvil Body -->
    <path d="M 35 90 C 35 70 20 60 0 50 L 120 50 C 100 60 85 70 85 90 Z" fill="#cbd5e1" />
    <!-- Anvil Horn & Top -->
    <path d="M -20 50 L 130 50 L 130 40 L -20 40 C -40 40 -40 50 -20 50 Z" fill="url(#accentGradient)" />
    
    <!-- Spark / AI Star above anvil -->
    <path d="M 60 -10 L 65 5 L 80 10 L 65 15 L 60 30 L 55 15 L 40 10 L 55 5 Z" fill="#60a5fa" />
    <path d="M 20 0 L 22 8 L 30 10 L 22 12 L 20 20 L 18 12 L 10 10 L 18 8 Z" fill="#3b82f6" opacity="0.8" />
  </g>

  <!-- Text -->
  <text x="200" y="340" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" 
        font-size="36" font-weight="900" fill="#ffffff" text-anchor="middle" letter-spacing="2">ROLE<tspan fill="#3b82f6">SMITH</tspan></text>
  <text x="200" y="365" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" 
        font-size="12" font-weight="600" fill="#9ca3af" text-anchor="middle" letter-spacing="4">AI PIPELINE</text>
</svg>
"""


def main():
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    logo_path = docs_dir / "logo.svg"
    with open(logo_path, "w", encoding="utf-8") as f:
        f.write(SVG_CONTENT)

    print(f"Generated beautifully coded SVG logo at: {logo_path}")


if __name__ == "__main__":
    main()
