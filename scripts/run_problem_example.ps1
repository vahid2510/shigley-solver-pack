# run_problem_example.ps1
# Example: parse a sample problem into ProblemSpec JSON
param(
  [string]$InPath = "samples/problems/beam_udl.txt",
  [string]$OutPath = "outputs/beam_spec.json"
)
python "tools/problem_spec_builder_v2.py" --in "$InPath" --out "$OutPath"