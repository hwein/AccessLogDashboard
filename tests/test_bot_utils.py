import re

from bot_utils import load_bot_list, is_bot


def test_load_bot_list(tmp_path):
    file = tmp_path / "bots.txt"
    file.write_text("botone\nbotTwo\n#comment\n\nbotone\n")
    bots = load_bot_list(str(file))
    assert bots == ["botTwo", "botone"] or bots == ["botone", "botTwo"]


def test_is_bot(monkeypatch):
    pattern = re.compile("bot", re.I)
    monkeypatch.setattr("bot_utils.BOT_PATTERN", pattern)
    assert is_bot("GreatBot/1.0")
    assert not is_bot("Mozilla/5.0")
