"""Split a Qualtrics CSV export into two CSVs with one row per valid trial."""

import argparse
import csv
import json
import math
import tempfile
from collections import Counter
from itertools import chain, islice
from pathlib import Path


# Both output files use the same columns, in the order returned by clean_trial.
COLUMNS = ("response_time_ms", "question_id", "word")
# Qualtrics exports the careless-response answer as the value "1" or "2".
FILENAMES = {"1": "careless_1.csv", "2": "careless_2.csv"}


def find_column(headers, name):
    # Prefer the embedded-data header and accept the unprefixed name as a fallback.
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
    # Without the ImportId marker, include the rows we read ahead to inspect.
    return chain(first_rows, reader)


def clean_trial(trial):
    if not isinstance(trial, dict):
        return None

    # Response times are in milliseconds. Accept only finite, nonnegative numbers.
    # The exact type check also rejects JSON booleans.
    rt = trial.get("rt")
    if type(rt) not in (int, float) or rt < 0:
        return None
    if isinstance(rt, float) and not math.isfinite(rt):
        return None

    # Question IDs can arrive as text or as positive integers.
    question_id = trial.get("id")
    if isinstance(question_id, str):
        question_id = question_id.strip()
        if not question_id:
            return None
    elif type(question_id) is not int or question_id <= 0:
        return None

    # Strip surrounding whitespace and reject blank selections.
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
        # All valid trials from this survey response go to the same output file.
        group = (row.get(careless_column) or "").strip()
        if group not in writers:
            counts["unknown_group"] += 1
            continue

        # Each Qualtrics response stores its trial list as JSON in one CSV cell.
        try:
            trials = json.loads(row.get(trials_column) or "")
        except (ValueError, RecursionError):
            counts["invalid_payload"] += 1
            continue
        if not isinstance(trials, list) or not trials:
            counts["invalid_payload"] += 1
            continue

        # Check each trial separately so one bad trial does not discard the rest.
        for trial in trials:
            cleaned = clean_trial(trial)
            if cleaned is None:
                counts["invalid_trial"] += 1
                continue
