from pathlib import Path

root = Path(__file__).resolve().parent
print("Root:", root)

print("\nContents of root:")
for p in root.iterdir():
    print(" -", p)

print("\nLooking for src/:", (root / "src").exists())
print("Looking for core/:", (root / "core").exists())
