import gettext
from os import walk, system, getcwd
import re

regex = r"Language-Team: (.*)"
languages = [dir for dir in walk("./locale")][0][1]
language_names = {}

for x in languages:
    cwd = getcwd().replace("\\", "/")  # windows lol
    system(
        "python "
        + cwd
        + "/utils/msgfmt.py "
        + cwd
        + "/locale/"
        + x
        + "/LC_MESSAGES/bot.po"
    )
    # open po file and get language team
    with open(
        cwd + "/locale/" + x + "/LC_MESSAGES/bot.po", "r", encoding="UTF-8"
    ) as file:
        if team := re.search(regex, file.read()):
            language_names[x] = (team.group(1)).replace('\\n"', "")


initilized_langs = {}

for x in languages:
    initilized_langs[x] = gettext.translation("bot", "./locale", languages=[x])

for lang in languages:
    initilized_langs[lang].install()
