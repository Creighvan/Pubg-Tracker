"""/ranked replaces the six per-queue commands; every queue still reaches the report code unchanged."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

import discord
import pytest

import commands.ranked as ranked_module
from commands.ranked import RANKED_QUEUES, ranked_impl
from pubg_api import PubgApiError

ROOT = Path(__file__).resolve().parent.parent
BOT = ast.parse((ROOT / "bot.py").read_text(encoding="utf-8"))
OLD = {"rankedsquad", "rankedduo", "rankedsolo", "rankedsquadfpp", "rankedduofpp", "rankedsolofpp"}


def _commands():
    return {n.name: n for n in BOT.body
            if isinstance(n, ast.AsyncFunctionDef) and any("tree.command" in ast.unparse(d) for d in n.decorator_list)}


def test_the_six_old_commands_are_gone_and_ranked_exists():
    cmds = _commands()
    assert not OLD & set(cmds)
    assert "ranked" in cmds and {"setrankedqueue", "setrankedchannel"} <= set(cmds)


def test_the_queue_is_optional_and_offers_the_same_six_choices_as_before():
    node = _commands()["ranked"]
    args = node.args
    names = [a.arg for a in args.args]
    assert names == ["interaction", "queue"] and len(args.defaults) == 1            # queue has a default: it is optional
    assert RANKED_QUEUES == {"squad": "Squad TPP", "duo": "Duo TPP", "solo": "Solo TPP",
                             "squad-fpp": "Squad FPP", "duo-fpp": "Duo FPP", "solo-fpp": "Solo FPP"}


def test_setrankedqueue_shares_the_same_list():
    src = (ROOT / "bot.py").read_text(encoding="utf-8")
    assert src.count("@app_commands.choices(queue=RANKED_QUEUE_CHOICES)") == 2        # /ranked and /setrankedqueue


class FakeInteraction:
    def __init__(self, expired=False):
        self.guild_id = 7
        self.guild = SimpleNamespace(name="Clan")
        self.sent = []
        self.expired = expired
        self.response = SimpleNamespace(defer=self._defer)
        self.followup = SimpleNamespace(send=self._send)

    async def _defer(self):
        if self.expired:
            raise discord.NotFound(SimpleNamespace(status=404, reason="x"), "Unknown interaction")

    async def _send(self, content=None, **kw):
        self.sent.append((content, kw))


@pytest.fixture
def env(monkeypatch):
    calls = []
    state = {"cfg": {"language": "en", "ranked_queue": "duo"}, "result": "ok"}

    async def get_guild(gid):
        return state["cfg"]

    async def fetch(gid, name, mode):
        calls.append(mode)
        if state["result"] == "error":
            raise PubgApiError("boom")
        return (discord.Embed(title="Ranked"), []) if state["result"] == "ok" else None

    monkeypatch.setattr(ranked_module.storage, "get_guild", get_guild)
    monkeypatch.setattr(ranked_module, "fetch_ranked_report", fetch)
    return calls, state


def run(**kw):
    i = FakeInteraction(**kw.pop("interaction", {}))
    asyncio.run(ranked_impl(i, None, **kw))
    return i


@pytest.mark.parametrize("queue", list(RANKED_QUEUES))
def test_every_queue_reaches_the_report_exactly_as_the_old_commands_did(env, queue):
    calls, _ = env
    i = run(queue=queue)
    assert calls == [queue] and i.sent[0][1]["embed"].title == "Ranked"


def test_no_queue_uses_the_servers_ranked_queue(env):
    calls, state = env
    run()
    assert calls == ["duo"]
    state["cfg"] = {"language": "en"}
    run()
    assert calls[-1] == "squad"                                   # the default when nothing is configured


def test_a_bad_value_falls_back_to_the_servers_queue(env):
    calls, _ = env
    run(queue="nonsense")
    assert calls == ["duo"]


def test_no_data_and_api_errors_give_clear_messages(env):
    _, state = env
    state["result"] = "none"
    assert run(queue="solo").sent[0][0]
    state["result"] = "error"
    assert "❌" in run(queue="solo").sent[0][0]


def test_an_expired_interaction_is_ignored_quietly(env):
    calls, _ = env
    i = run(interaction={"expired": True}, queue="squad")
    assert calls == [] and i.sent == []
