import csv
import glob
import os
import re

log_dir = os.path.join(os.path.dirname(__file__), "../../benchmark_logs")
log_file_paths = sorted(glob.glob(os.path.join(log_dir, "*.log")))
output_csv = os.path.join(log_dir, "raw.csv")

LINE_RE = re.compile(
    r"ProcessBlock\/([^\/]+)\/([^\/]+)\/([0-9]+)"
    r"\/iteration:([0-9]+)\/repetition:([0-9]+)\s+([\d.]+)\s+ms"
)


def get_list_from_log(file_path: str, log_list: list | None = None) -> list:
    if log_list is None:
        log_list = [[], [], [], [], [], [], [], []]
        rep_index = 0
    else:
        rep_index = max(log_list[4])

    old_rep_count = 0
    with open(file_path, "r") as file:
        for line in file:
            if "ProcessBlock/" not in line or "iteration:" not in line:
                continue
            match = LINE_RE.search(line)
            if match is None:
                raise ValueError(f"Unexpected log line in {file_path}:\n  {line.rstrip()}")
            rep_count = int(match.group(5))
            if old_rep_count != rep_count:
                rep_index += 1
                old_rep_count = rep_count
            env = os.path.splitext(os.path.basename(file_path))[0]
            log_list[0].append(env)
            log_list[1].append(match.group(1))   # model
            log_list[2].append(match.group(2))   # run
            log_list[3].append(int(match.group(3)))  # buffer size
            log_list[4].append(rep_index)
            log_list[5].append(rep_count)
            log_list[6].append(int(match.group(4)))  # iteration
            log_list[7].append(float(match.group(6)))  # runtime ms

    return log_list


def write_list_to_csv(file_path: str, log_list: list) -> None:
    with open(file_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Environment", "Model", "Run",
            "Buffer Size", "Repetition Index", "Repetition Count",
            "Iteration Count", "Runtime",
        ])
        writer.writerows(zip(*log_list))


if __name__ == "__main__":
    if not log_file_paths:
        raise FileNotFoundError(f"No .log files found in {log_dir}")
    log_list = None
    for path in log_file_paths:
        log_list = get_list_from_log(path, log_list)
    write_list_to_csv(output_csv, log_list)
    envs = sorted({os.path.splitext(os.path.basename(p))[0] for p in log_file_paths})
    print(f"raw.csv written ({len(log_list[0])} rows, environments: {', '.join(envs)})")
