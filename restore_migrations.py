import os

base = r"c:\Users\pranaldongare\VisualCodeProjects\AITutorPlatform\backend\migrations"
print(f"Checking directory: {base}")

try:
    files = os.listdir(base)
except Exception as e:
    print(f"Error listing dir: {e}")
    exit(1)

count = 0
for f in files:
    if f.endswith(".disabled"):
        src = os.path.join(base, f)
        dst = os.path.join(base, f.replace(".disabled", ""))
        try:
            os.rename(src, dst)
            print(f"Restored: {f} -> {dst}")
            count += 1
        except Exception as e:
            print(f"Failed to restore {f}: {e}")

print(f"Total restored: {count}")
