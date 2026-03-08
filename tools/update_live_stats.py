import sqlite3, re, subprocess, sys, os

DB_PATH   = r"C:\Users\ajsup\.neuralmemory\brains\default.db"
REPO_PATH = r"C:\Users\ajsup\adam-framework-public"
README    = os.path.join(REPO_PATH, "README.md")
INDEX     = os.path.join(REPO_PATH, "index.html")

def get_counts():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    neurons  = cur.execute("SELECT COUNT(*) FROM neurons").fetchone()[0]
    synapses = cur.execute("SELECT COUNT(*) FROM synapses").fetchone()[0]
    con.close()
    return neurons, synapses

def fmt(n):
    return f"{n:,}"

def update_file(path, neurons, synapses):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    original = content

    # "12,393 neurons / 40,532 synapses" pattern (arch box, README body)
    content = re.sub(
        r'\d[\d,]+ neurons \/ \d[\d,]+ synapses',
        f"{fmt(neurons)} neurons / {fmt(synapses)} synapses",
        content
    )
    # "12,393 neurons. 40,532 synapses." (boot log / proof text)
    content = re.sub(
        r'\d[\d,]+ neurons\. \d[\d,]+ synapses\.',
        f"{fmt(neurons)} neurons. {fmt(synapses)} synapses.",
        content
    )
    # README proof table rows
    content = re.sub(
        r'(Neural graph neurons \|[^\n]*\|)\s*[\d,]+',
        lambda m: m.group(1) + " " + fmt(neurons),
        content
    )
    content = re.sub(
        r'(Neural graph synapses \|[^\n]*\|)\s*[\d,]+',
        lambda m: m.group(1) + " " + fmt(synapses),
        content
    )
    # index.html hero stat: <div class="hero-stat-num">12,393</div>...<div class="hero-stat-label">Neurons
    content = re.sub(
        r'(<div class="hero-stat-num">)\d[\d,]+(</div><div class="hero-stat-label">Neurons)',
        lambda m: m.group(1) + fmt(neurons) + m.group(2),
        content
    )
    # index.html proof grid: proof-num followed by proof-label mentioning neurons/synapses
    content = re.sub(
        r'(<div class="proof-num">)\d[\d,]+(</div><div class="proof-label">Neural graph neurons)',
        lambda m: m.group(1) + fmt(neurons) + m.group(2),
        content
    )
    content = re.sub(
        r'(<div class="proof-num">)\d[\d,]+(</div><div class="proof-label">Neural graph synapses)',
        lambda m: m.group(1) + fmt(synapses) + m.group(2),
        content
    )
    # index.html ticker spans
    content = re.sub(r'(?<=>)\d[\d,]+(?= neurons<)', fmt(neurons), content)
    content = re.sub(r'(?<=>)\d[\d,]+(?= synapses<)', fmt(synapses), content)
    # arch layer description: "12,393 neurons built from"
    content = re.sub(r'\d[\d,]+ neurons built from', f"{fmt(neurons)} neurons built from", content)

    if content != original:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
        return True
    return False

def git(args, cwd):
    result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def main():
    neurons, synapses = get_counts()
    print(f"Live stats: {fmt(neurons)} neurons, {fmt(synapses)} synapses")

    readme_changed = update_file(README, neurons, synapses)
    index_changed  = update_file(INDEX,  neurons, synapses)

    if not readme_changed and not index_changed:
        print("Stats unchanged — nothing to commit.")
        return

    changed = []
    if readme_changed: changed.append("README.md")
    if index_changed:  changed.append("index.html")
    print(f"Updated: {', '.join(changed)}")

    git(["add"] + changed, REPO_PATH)
    msg = f"chore: live stats update — {fmt(neurons)} neurons, {fmt(synapses)} synapses"
    rc, out, err = git(["commit", "-m", msg], REPO_PATH)
    if rc != 0:
        print(f"Commit failed: {err}")
        sys.exit(1)
    print(f"Committed: {out}")

    git(["pull", "--rebase"], REPO_PATH)
    rc, out, err = git(["push"], REPO_PATH)
    if rc != 0:
        print(f"Push failed: {err}")
        sys.exit(1)
    print(f"Pushed.")

if __name__ == "__main__":
    main()
