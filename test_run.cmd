
@echo off
REM Example Windows usage (edit the PDF path):
set PDF="C:\Users\Administrator\Desktop\Shigly Project\Shigley’s Mechanical Engineering Design.pdf"
python shigley_problem_harvester.py --pdf %PDF% --out harvest_all.json
python make_dataset.py --in harvest_all.json --per-topic 15 --out dataset_per_topic.json
echo Done.
