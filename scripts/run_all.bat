@echo off
REM run_all.bat — build spec for all sample problems
python "tools\problem_spec_builder_v2.py" --in "samples\problems\beam_udl.txt" --out "outputs\beam_spec.json"
python "tools\problem_spec_builder_v2.py" --in "samples\problems\pv_cylinder.txt" --out "outputs\pv_spec.json"
python "tools\problem_spec_builder_v2.py" --in "samples\problems\column_buckling.txt" --out "outputs\column_spec.json"
python "tools\problem_spec_builder_v2.py" --in "samples\problems\sdof_base.txt" --out "outputs\sdof_spec.json"
echo Done.