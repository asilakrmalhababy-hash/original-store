import os, re, subprocess

css_path = "client/src/index.css"
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

old_lines = len(css.splitlines())
marker_v168 = "/* === ORIGINAL CLEAN V168 START === */"
if marker_v168 not in css:
    raise RuntimeError("لم يتم العثور على بداية V168")

head_part, v168_part = css.split(marker_v168, 1)

# تحديد بداية كتلة v165/v166 المتبقية بدقة وقصها بالكامل حتى بداية V168
idx_em = head_part.find("--orig-em-dark: #0b2b1d;")
if idx_em != -1:
    cut_start = head_part.rfind(":root", 0, idx_em)
    if cut_start != -1:
        head_part = head_part[:cut_start]

# إزالة أي بقايا تعليق END إن وجدت
head_part = re.sub(r'/\* === ORIGINAL MASTER.*?END === \*/', '', head_part)
new_css = head_part.rstrip() + "\n\n" + marker_v168 + v168_part

# فحص نهائي للتأكد 100% من اختفاء أي قاعدة تخفي حسابي من v165 أو v166
leftover = re.findall(r'orig-acc-v16[56]-root', new_css)
if leftover:
    raise RuntimeError(f"لا تزال هناك بقايا: {leftover}")

with open(css_path, "w", encoding="utf-8") as f:
    f.write(new_css.rstrip() + "\n")

new_lines = len(new_css.splitlines())
print(f"✅ تم تنظيف client/src/index.css من {old_lines} سطر إلى {new_lines} سطر (0 بقايا v165/v166)!")

subprocess.run(["git", "add", "client/src/index.css"], check=True)
subprocess.run(["git", "commit", "-m", "Fix v169: purge orphaned v165/v166 CSS rules in index.css hiding account page"], check=False)

res = subprocess.run(["git", "push", "origin", "main"])
if res.returncode != 0:
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -p 443 -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"
    subprocess.run(["git", "push", "ssh://git@ssh.github.com:443/asilakrmalhababy-hash/original-store.git", "main"], env=env, check=True)

print("🚀 تم رفع الإصلاح v169 إلى Render بنجاح!")
