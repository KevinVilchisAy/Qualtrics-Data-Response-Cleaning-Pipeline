"""Split a Qualtrics CSV export into two CSVs with one row per valid trial."""

import argparse
import csv
import json
import math
import tempfile
from collections import Counter
from itertools import chain, islice
from pathlib import Path


COLUMNS = ("response_time_ms", "question_id", "word")
FILENAMES = {"1": "careless_1.csv", "2": "careless_2.csv"}


def find_column(headers, name):
    for candidate in ("__js_" + name, name):
        if candidate in headers:
            return candidate
    raise ValueError(f"Missing CSV column: __js_{name}")


def response_rows(reader, trials_column):
    # Standard Qualtrics exports put a label row before the ImportId row.
    first_rows = list(islice(reader, 2))
    for index, row in enumerate(first_rows):
        cell = (row.get(trials_column) or "").strip()
        if cell.startswith("{") and '"ImportId"' in cell:
            return chain(first_rows[index + 1:], reader)
    return chain(first_rows, reader)


def clean_trial(trial):
    if not isinstance(trial, dict):
        return None

    rt = trial.get("rt")
    if type(rt) not in (int, float) or rt < 0:
        return None
    if isinstance(rt, float) and not math.isfinite(rt):
        return None

    question_id = trial.get("id")
    if isinstance(question_id, str):
        question_id = question_id.strip()
        if not question_id:
            return None
    elif type(question_id) is not int or question_id <= 0:
        return None

    word = trial.get("word")
    if not isinstance(word, str) or not word.strip():
        return None

    return rt, question_id, word.strip()


def split_responses(reader, writers):
    headers = [header.strip() for header in (reader.fieldnames or [])]
    reader.fieldnames = headers
    careless_column = find_column(headers, "careless")
    trials_column = find_column(headers, "trials_json")
    counts = Counter()

    for row in response_rows(reader, trials_column):
        group = (row.get(careless_column) or "").strip()
        if group not in writers:
            counts["unknown_group"] += 1
            continue

        try:
            trials = json.loads(row.get(trials_column) or "")
        except (ValueError, RecursionError):
            counts["invalid_payload"] += 1
            continue
        if not isinstance(trials, list) or not trials:
            counts["invalid_payload"] += 1
            continue

        for trial in trials:
            cleaned = clean_trial(trial)
            if cleaned is None:
                counts["invalid_trial"] += 1
                continue
            writers[group].writerow(cleaned)
            counts[group] += 1

    return counts


def run_pipeline(source, output_dir):
    output_paths = [output_dir / name for name in FILENAMES.values()]
    if source.resolve() in [path.resolve() for path in output_paths]:
        raise ValueError("The input CSV must be separate from the output files.")
