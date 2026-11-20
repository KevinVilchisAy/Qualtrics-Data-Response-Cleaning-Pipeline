# Qualtrics Data Cleaning Pipeline

This Python pipeline turns a Qualtrics survey export into two CSV files for response-time analysis. It extracts the trials recorded for each survey response, separates them by the participant’s answer to the careless-response question, and keeps only the time, question ID, and selected word for each valid trial.

## How it works

1. **Read the export.** The pipeline reads the survey responses from a Qualtrics CSV and skips the export’s metadata rows when present.
2. **Clean the trials.** It unpacks the recorded trials and checks that each one has a valid response time, a question ID, and a selected word. It reports how many responses or trials it skipped.
3. **Split and save.** It writes one row per valid trial to the file that matches the response’s `__js_careless` value. The original Qualtrics export stays intact.

## Run the pipeline

Export the survey results from Qualtrics as a **CSV**. Select **Export values** and keep **Download all fields** checked. If Qualtrics downloads a ZIP file, extract the CSV first.

With Python 3.10 or newer installed, open a terminal in the folder containing the script and the export. The pipeline uses Python’s standard library, so there are no extra packages to install.

```bash
python3 qualtrics_data_cleaning_pipeline.py "qualtrics_export.csv"
```

Replace `qualtrics_export.csv` with your actual filename. Keep the quotes if the filename contains spaces.

## Output files

| File | Survey response group |
| --- | --- |
| `cleaned/careless_2.csv` | `__js_careless` is `2` |
| `cleaned/careless_1.csv` | `__js_careless` is `1` |

Both files contain the same three columns:

| Column | Description |
| --- | --- |
| `response_time_ms` | Time to select a word, in milliseconds |
| `question_id` | ID of the question shown |
| `word` | Word selected by the participant |
