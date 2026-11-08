"""
Text colours the question editor offers. Mid-tones on purpose: the pupil app has a light and a
dark theme, and these stay readable on both. Black or white text would vanish in one of them.

Shared by the editor configuration (settings.py) and the HTML cleaner (richtext.py), which keeps
only these colours, so a colour pasted from Word can't sneak in. No Django imports here: settings
imports this module.
"""

TEXT_COLOURS = {
    "#e0453a": "Qizil",
    "#2f7de1": "Ko‘k",
    "#2e9e4f": "Yashil",
    "#e8710a": "To‘q sariq",
    "#9c4dcc": "Binafsha",
}
