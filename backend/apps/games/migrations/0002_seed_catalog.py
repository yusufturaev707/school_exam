"""
The catalogue is required for the app to work at all, so it is created by a migration rather than a
command someone could forget. It runs once: later edits made in the admin are never overwritten.
"""

from django.db import migrations

LEVELS = ["easy", "medium", "hard"]

GAMES = [
    {
        "slug": "xotira-kartalari",
        "kind": "memory",
        "title": "Xotira kartalari",
        "description": "Bir xil rasmli kartalarni juft-juft qilib top.",
        "category": "memory",
        "duration_minutes": 3,
        "is_active": True,
        "intro_title": "Xotirangni sinab ko‘rishga tayyormisan?",
        "intro_text": "Bir xil rasmlarni top va barcha kartalarni och!",
        "instructions": [
            "Ikkita kartani bosib och.",
            "Rasmlar bir xil bo‘lsa, ular ochiq qoladi.",
            "Har xil bo‘lsa, kartalar yana yopiladi — joyini eslab qol!",
        ],
    },
    {
        "slug": "yashiringan-son",
        "kind": "missing-number",
        "title": "Yashiringan son",
        "description": "Sonlar qatoridagi qonuniyatni top va bo‘sh joyni to‘ldir.",
        "category": "math",
        "duration_minutes": 4,
        "is_active": True,
        "intro_title": "Sonlar sirini ochamizmi?",
        "intro_text": "Qatordagi sonlar bir qoidaga bo‘ysunadi. Yashiringan sonni top!",
        "instructions": [
            "Sonlar qatoriga diqqat bilan qara.",
            "Ular qanday o‘zgarayotganini top: qo‘shilyaptimi, ko‘paytirilyaptimi?",
            "To‘rtta javobdan to‘g‘risini tanla.",
        ],
    },
    {
        "slug": "naqsh-ustasi",
        "kind": "pattern",
        "title": "Naqsh ustasi",
        "description": "Shakllar qatori qanday davom etishini top.",
        "category": "logic",
        "duration_minutes": 4,
        "is_active": True,
        "intro_title": "Naqsh ustasi bo‘lishga tayyormisan?",
        "intro_text": "Shakllar, ranglar va burilishlardagi qoidani top — keyingisi qaysi?",
        "instructions": [
            "Shakllar qatoriga qara: shakl, rang, son va yo‘nalish o‘zgarishi mumkin.",
            "Qaysi qoida takrorlanayotganini top.",
            "Qatorni davom ettiradigan shaklni tanla.",
        ],
    },
    {
        "slug": "ortiqchasini-top",
        "kind": "odd-one-out",
        "title": "Ortiqchasini top",
        "description": "Guruhga mos kelmaydigan narsani aniqla.",
        "category": "attention",
        "duration_minutes": 3,
        "is_active": False,
        "intro_title": "Ortiqchasini topa olasanmi?",
        "intro_text": "Bittasi guruhga mos emas. Qaysi biri?",
        "instructions": [],
    },
    {
        "slug": "tez-hisob",
        "kind": "quick-math",
        "title": "Tez hisob",
        "description": "Og‘zaki hisoblashni mashq qil — 10 ta misol.",
        "category": "math",
        "duration_minutes": 3,
        "is_active": False,
        "intro_title": "Hisoblashga tayyormisan?",
        "intro_text": "10 ta qiziqarli misol seni kutmoqda.",
        "instructions": [],
    },
    {
        "slug": "labirint",
        "kind": "maze",
        "title": "Labirint",
        "description": "Do‘stingni labirintdan chiqishga olib bor.",
        "category": "spatial",
        "duration_minutes": 4,
        "is_active": False,
        "intro_title": "Yo‘lni topa olasanmi?",
        "intro_text": "Devorlardan o‘tib bo‘lmaydi — chiqishni top!",
        "instructions": [],
    },
    {
        "slug": "sozlar-qidiruvi",
        "kind": "word-search",
        "title": "So‘zlar qidiruvi",
        "description": "Harflar orasiga yashiringan so‘zlarni top.",
        "category": "language",
        "duration_minutes": 5,
        "is_active": False,
        "intro_title": "So‘z ovchisi bo‘lamizmi?",
        "intro_text": "Harflar orasidan so‘zlarni top.",
        "instructions": [],
    },
]

DAILY_QUESTIONS = [
    {
        "prompt": "Qaysi son ortiqcha?",
        "sequence": "3 · 9 · 12 · 27 · 81",
        "options": ["3", "9", "12", "81"],
        "correct_option": "12",
        "explanation": "Qolganlari 3 ning darajalari: 3, 9, 27, 81.",
    },
    {
        "prompt": "Keyingi son qaysi?",
        "sequence": "2 · 4 · 8 · 16 · ?",
        "options": ["18", "24", "32", "20"],
        "correct_option": "32",
        "explanation": "Har bir son oldingisidan 2 marta katta.",
    },
    {
        "prompt": "Qaysi soʻz ortiqcha?",
        "sequence": "olma · nok · sabzi · uzum",
        "options": ["olma", "nok", "sabzi", "uzum"],
        "correct_option": "sabzi",
        "explanation": "Sabzi — sabzavot, qolganlari meva.",
    },
    {
        "prompt": "Keyingi son qaysi?",
        "sequence": "1 · 1 · 2 · 3 · 5 · ?",
        "options": ["6", "7", "8", "9"],
        "correct_option": "8",
        "explanation": "Har bir son oldingi ikkitasining yigʻindisi.",
    },
    {
        "prompt": "Qaysi son ortiqcha?",
        "sequence": "5 · 10 · 15 · 21 · 25",
        "options": ["10", "15", "21", "25"],
        "correct_option": "21",
        "explanation": "Qolganlari 5 ga boʻlinadi.",
    },
    {
        "prompt": "Yetishmayotgan son?",
        "sequence": "10 · 7 · ? · 1",
        "options": ["3", "4", "5", "6"],
        "correct_option": "4",
        "explanation": "Har qadamda 3 kamayadi.",
    },
    {
        "prompt": "Qaysi soʻz ortiqcha?",
        "sequence": "doira · kvadrat · uchburchak · qalam",
        "options": ["doira", "kvadrat", "uchburchak", "qalam"],
        "correct_option": "qalam",
        "explanation": "Qalam — shakl emas.",
    },
]


def seed(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    DailyQuestion = apps.get_model("games", "DailyQuestion")
    for order, game in enumerate(GAMES):
        Game.objects.create(difficulties=LEVELS, order=order, **game)
    for order, question in enumerate(DAILY_QUESTIONS):
        DailyQuestion.objects.create(order=order, **question)


class Migration(migrations.Migration):
    dependencies = [("games", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
