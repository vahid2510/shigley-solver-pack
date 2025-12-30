# run_lexicon_example.ps1
# Example: build 80k-entry dictionary from Shigley.pdf to outputs/lexicon
param(
  [string]$PdfPath = "Shigley.pdf",
  [string]$OutDir = "outputs/lexicon"
)
python "tools/shigley_lexicon_builder.py" "$PdfPath" "$OutDir" --target 80000