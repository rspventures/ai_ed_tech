import os

base = r"c:\Users\pranaldongare\VisualCodeProjects\AITutorPlatform\backend\migrations"
print(f"Checking directory: {base}")

try:
    files = os.listdir(base)
    print(f"Files found: {files}")
except Exception as e:
    print(f"Error listing dir: {e}")
    exit(1)

count = 0
for f in files:
    if f.endswith(".sql") and f != "00_create_langfuse_db.sql":
        src = os.path.join(base, f)
        dst = os.path.join(base, f + ".disabled")
        try:
            os.rename(src, dst)
            print(f"Renamed: {f} -> {f}.disabled")
            count += 1
        except Exception as e:
            print(f"Failed to rename {f}: {e}")

print(f"Total renamed: {count}")
