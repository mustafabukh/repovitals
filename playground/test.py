import subprocess

import pandas as pd

# unique char
SEP = "\x1f"
# hash, name, email, timestamp, subject.
LOG_FORMAT = SEP.join(["", "C", "%H", "%an", "%ae", "%at", "%s"])
print(LOG_FORMAT)


def run_git_log(repo_path):
    """runs:
    git log --no-merges --numstat --pretty=format:C%H%an%ae%at%s
    from the path of the repo we want to analyze"""
    command = [
        "git",
        "log",
        "--no-merges",
        "--numstat",
        "--pretty=format:" + LOG_FORMAT,
    ]
    result = subprocess.run(
        command,
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )

    return result.stdout


# import time
def parse_count(value):
    # print(value)
    if value == "-":
        # time.sleep(1)
        return 0
    return int(value)


def clean_path(path):
    if "=>" not in path:
        return path

    if "{" in path:
        start = path.index("{")
        end = path.index("}")
        new_part = path[start + 1 : end].split("=>")[1].strip()
        path = path[:start] + new_part + path[end + 1 :]
        return path.replace("//", "/").lstrip("/")

    return path.split("=>")[1].strip()


def parse_log(text):
    """raw git log output to list of dictionaries"""
    rows = []
    commit = None

    for line in text.split("\n"):
        if line.startswith(SEP):
            parts = line.split(SEP)
            commit = {
                "sha": parts[2],
                "author_name": parts[3],
                "author_email": parts[4],
                "timestamp": int(parts[5]),
                "subject": parts[6],
            }
        elif line.strip() == "" or commit is None:
            continue
        else:
            added, deleted, path = line.split("\t", 2)
            row = dict(commit)
            row["added"] = parse_count(added)
            row["deleted"] = parse_count(deleted)
            row["path"] = clean_path(path)
            row["is_binary"] = added == "-"
            row["was_renamed"] = "=>" in path
            rows.append(row)

    return rows


def load_history(repo_path):
    """Return a DataFrame with one row per file changed per commit."""
    rows = parse_log(run_git_log(repo_path))
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    return df


if __name__ == "__main__":
    df = load_history("playground/repos/requests")

    print("rows (file changes):", len(df))
    print("commits:", df["sha"].nunique())
    print("binary rows:", df["is_binary"].sum())
    print("rename rows:", df["was_renamed"].sum())
    print("author names:", df["author_name"].nunique())
    print("author emails:", df["author_email"].nunique())
    print()
    print("top 10 authors by commits:")
    print(
        df.groupby("author_name")["sha"].nunique().sort_values(ascending=False).head(10)
    )
    print()
    print("top 10 files by churn:")
    df["churn"] = df["added"] + df["deleted"]
    print(df.groupby("path")["churn"].sum().sort_values(ascending=False).head(10))
