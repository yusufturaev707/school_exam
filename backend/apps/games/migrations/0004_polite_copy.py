"""
Game texts now address the pupil politely ("siz"). As with the original seed, edits made in the admin
are never overwritten: a field changes only while it still holds the text 0002 put there.
"""

from importlib import import_module

from django.db import migrations

SEEDED = {game["slug"]: game for game in import_module("apps.games.migrations.0002_seed_catalog").GAMES}

COPY = {
    "xotira-kartalari": {
        "description": "Bir xil rasmli kartalarni juft-juft qilib toping.",
        "intro_title": "Xotirangizni sinab koʻrishga tayyormisiz?",
        "intro_text": "Bir xil rasmlarni toping va barcha kartalarni oching!",
        "instructions": [
            "Ikkita kartani bosib oching.",
            "Rasmlar bir xil boʻlsa, ular ochiq qoladi.",
            "Har xil boʻlsa, kartalar yana yopiladi — joyini eslab qoling!",
        ],
    },
    "yashiringan-son": {
        "description": "Sonlar qatoridagi qonuniyatni toping va boʻsh joyni toʻldiring.",
        "intro_text": "Qatordagi sonlar bir qoidaga boʻysunadi. Yashiringan sonni toping!",
        "instructions": [
            "Sonlar qatoriga diqqat bilan qarang.",
            "Ular qanday oʻzgarayotganini toping: qoʻshilyaptimi, koʻpaytirilyaptimi?",
            "Toʻrtta javobdan toʻgʻrisini tanlang.",
        ],
    },
    "naqsh-ustasi": {
        "description": "Shakllar qatori qanday davom etishini toping.",
        "intro_title": "Naqsh ustasi boʻlishga tayyormisiz?",
        "intro_text": "Shakllar, ranglar va burilishlardagi qoidani toping — keyingisi qaysi?",
        "instructions": [
            "Shakllar qatoriga qarang: shakl, rang, son va yoʻnalish oʻzgarishi mumkin.",
            "Qaysi qoida takrorlanayotganini toping.",
            "Qatorni davom ettiradigan shaklni tanlang.",
        ],
    },
    "ortiqchasini-top": {
        "title": "Ortiqchasini toping",
        "description": "Guruhga mos kelmaydigan narsani aniqlang.",
        "intro_title": "Ortiqchasini topa olasizmi?",
    },
    "tez-hisob": {
        "description": "Ogʻzaki hisoblashni mashq qiling — 10 ta misol.",
        "intro_title": "Hisoblashga tayyormisiz?",
        "intro_text": "10 ta qiziqarli misol sizni kutmoqda.",
    },
    "labirint": {
        "description": "Doʻstingizni labirintdan olib chiqing.",
        "intro_title": "Yoʻlni topa olasizmi?",
        "intro_text": "Devorlardan oʻtib boʻlmaydi — chiqishni toping!",
    },
    "sozlar-qidiruvi": {
        "title": "Soʻzlar qidiruvi",
        "description": "Harflar orasiga yashiringan soʻzlarni toping.",
        "intro_title": "Soʻz ovchisi boʻlamizmi?",
        "intro_text": "Harflar orasidan soʻzlarni toping.",
    },
}


def use_polite_copy(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    for game in Game.objects.filter(slug__in=COPY):
        untouched = [
            field for field in COPY[game.slug] if getattr(game, field) == SEEDED[game.slug][field]
        ]
        for field in untouched:
            setattr(game, field, COPY[game.slug][field])
        if untouched:
            game.save(update_fields=untouched)


class Migration(migrations.Migration):
    dependencies = [("games", "0003_verbose_names")]

    operations = [migrations.RunPython(use_polite_copy, migrations.RunPython.noop)]
