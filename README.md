# OMR Processing System

## Input
- `student_file`: scanned OMR sheet image (`PNG/JPG`)
- `answer_key_file`: answer sheet image (`PNG/JPG`)

## Example with `img.png`
Run the server:

```bash
python main.py
```

Evaluate using the existing sample image as both inputs:

```bash
curl -X POST http://127.0.0.1:5000/evaluate \
  -F "student_file=@img.png" \
  -F "answer_key_file=@img.png" \
  -F "question_count=150" \
  -F "options=[\"A\",\"B\",\"C\",\"D\"]"
```

The API returns:
- `score_summary`
- `student_answers`
- `answer_key_answers`
- `comparison`
- `pdf_filename`
- `pdf_base64`

Use a real answer-key image instead of `img.png` for actual scoring.

Notes:
- uploaded student and answer-key images are deleted after processing
- the PDF is generated in memory and is not stored on disk
