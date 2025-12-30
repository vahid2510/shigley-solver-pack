
#!/usr/bin/env bash
# Example Unix usage (edit PDF path)
PDF="/path/to/Shigley’s Mechanical Engineering Design.pdf"
python3 shigley_problem_harvester.py --pdf "$PDF" --out harvest_all.json
python3 make_dataset.py --in harvest_all.json --per-topic 15 --out dataset_per_topic.json
echo "Done."
