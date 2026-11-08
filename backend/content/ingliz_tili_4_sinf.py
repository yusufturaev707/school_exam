"""
The 4th-grade English test: 30 questions, one subject ("language", shown as "Ingliz tili").

Source: content/sources/ingliz_tili_4_sinf_turli_testlar_v2.json, a list of
{"id", "question", "options": ["A) …", …], "answer": "B) …"}. This script turns it into the format
`import_exam` reads and writes ingliz-tili-4-sinf.json next to itself:

    python content/ingliz_tili_4_sinf.py

The source is checked as it is read: every option must start with its letter in order, and the
answer must be one of the options, so a typo in the source can't produce a wrong answer key.
"""

import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "sources" / "ingliz_tili_4_sinf_turli_testlar_v2.json"
TARGET = HERE / "ingliz-tili-4-sinf.json"

# Spelling fixed in the source's Uzbek wording.
FIXES = {
    "muqvili": "muqobili",
    "antonom": "antonim",
    "a'zo": "a’zo",
    "ma'no": "ma’no",
}

# 1 oson, 2 o‘rta, 3 qiyin. Shuffling keeps this order inside the test: easier questions first.
# 1–10 words, 11–15 "to be", 16–20 plurals, 21–25 everyday phrases, 26–30 numbers and opposites.
EASY, MEDIUM, HARD = 1, 2, 3
DIFFICULTY = {
    **dict.fromkeys(range(1, 11), EASY),
    **dict.fromkeys(range(11, 16), MEDIUM),
    16: MEDIUM,
    17: HARD,  # box → boxes: the -es ending
    18: MEDIUM,
    19: MEDIUM,
    20: MEDIUM,
    21: EASY,
    22: MEDIUM,
    23: MEDIUM,
    24: EASY,
    25: EASY,
    26: EASY,
    27: MEDIUM,
    28: MEDIUM,
    29: MEDIUM,
    30: HARD,  # translation and the article together
}

OPTION = re.compile(r"^([A-Z])\)\s*(.+)$")


def fixed(text: str) -> str:
    for wrong, right in FIXES.items():
        text = text.replace(wrong, right)
    return " ".join(text.split())


def paragraph(text: str) -> str:
    return f"<p>{html.escape(fixed(text), quote=False)}</p>"


def question(item: dict) -> dict:
    number = item["id"]
    options = []
    for expected, raw in zip("ABCDEFGHIJ", item["options"], strict=False):
        match = OPTION.match(raw.strip())
        if not match or match.group(1) != expected:
            raise ValueError(f"Savol {number}: variant “{raw}” “{expected}) …” bo‘lishi kerak.")
        options.append((match.group(1), match.group(2)))
    correct = [label for label, text in options if f"{label}) {text}" == item["answer"].strip()]
    if len(correct) != 1:
        raise ValueError(f"Savol {number}: javob “{item['answer']}” variantlar orasida yo‘q.")
    return {
        "number": number,
        "subject": "language",
        "type": "single_choice",
        "difficulty": DIFFICULTY[number],
        "prompt": paragraph(item["question"]),
        "passage": "",
        "explanation": "",
        "options": [
            {"label": label, "content": paragraph(text), "isCorrect": label == correct[0]}
            for label, text in options
        ],
    }


def build() -> dict:
    items = json.loads(SOURCE.read_text(encoding="utf-8"))
    questions = [question(item) for item in items]
    numbers = [q["number"] for q in questions]
    if numbers != list(range(1, len(questions) + 1)):
        raise ValueError("Savollar 1 dan boshlab ketma-ket raqamlangan bo‘lishi kerak.")
    return {
        "title": "4-sinf bitiruvchilari uchun ingliz tili testi",
        "description": "Ingliz tili bo‘yicha 30 ta savol: so‘z boyligi, grammatika (to be, "
        "ko‘plik) va muloqot. Har bir to‘g‘ri javob 1 ball, eng yuqori natija 30 ball.",
        "durationMinutes": 45,
        "pointsPerQuestion": 1,
        # Everybody gets the same questions: showing the answers to whoever finishes first
        # would hand them to the pupils who haven't started yet.
        "reviewEnabled": False,
        "shuffleQuestions": True,
        "shuffleOptions": True,
        "grades": [4],
        "sections": [{"subject": "language", "title": "Ingliz tili"}],
        "questions": questions,
    }


if __name__ == "__main__":
    TARGET.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {TARGET}")
