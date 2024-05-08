import json
from dataclasses import dataclass
from typing import Union

import zstandard
from datetime import timedelta
from fafreplay import Parser, commands

all_commands = [commands.Advance, commands.SetCommandSource, commands.CommandSourceTerminated,
                commands.VerifyChecksum,
                commands.RequestPause, commands.Resume, commands.SingleStep,
                commands.CreateUnit, commands.CreateProp,
                commands.DestroyEntity, commands.WarpEntity,
                commands.ProcessInfoPair, commands.IssueCommand,
                commands.IssueFactoryCommand,
                commands.IncreaseCommandCount, commands.DecreaseCommandCount,
                commands.SetCommandTarget, commands.SetCommandType, commands.SetCommandCells,
                commands.RemoveCommandFromQueue,
                commands.DebugCommand,
                commands.ExecuteLuaInSim, commands.LuaSimCallback,
                commands.EndGame]

MSG_TICK_TIMEOUT = 20  # for deduplication
MSG_DONE_SUFFIX = "done!"
MSG_DONE_SUFFIX2 = "construction done!"


class MessageTypes:
    all = "all"
    allies = "allies"
    auto_notify = "notify"


@dataclass(frozen=True)
class ChatMessage:
    ally_only: bool
    player: str
    message: str
    sent_at_sec: float


@dataclass(frozen=True)
class CompletionNotification:
    player: str
    completed: str
    sent_at_sec: float


@dataclass(frozen=True)
class ResourceSent:
    from_player: str
    to_player: str
    mass: float
    energy: float
    sent_at_sec: float


@dataclass
class ReplayPlayerMetadata:
    player_id: str
    nickname: str
    clan: str
    country: str

    rating_mean: float
    rating_std: float
    rating: float

    faction: int
    team: int


@dataclass
class ReplayMetadata:
    title: str
    replay_id: str

    chat_messages: list[ChatMessage]
    notifications: list[CompletionNotification]
    resource_transfer: list[ResourceSent]

    launched_at_ts: int
    duration: float
    map: str

    game_type: str
    desync: bool
    players: list[ReplayPlayerMetadata]


def ensure_str(str_or_bytes: Union[str, bytes]):
    if isinstance(str_or_bytes, bytes):
        try:
            return str_or_bytes.decode()
        except UnicodeDecodeError:
            return ""
    return str_or_bytes


# Based on `fafreplay`'s extract_scfa function
def extract_scfa(fobj):
    """Turns data from `.fafreplay` format into `.scfareplay` format."""
    header = json.loads(fobj.readline().decode())
    buf = fobj.read()
    compression_type = header.get("compression")

    if compression_type == "zlib":
        raise Exception("Cannot decode zstd compression type, as they lack header")
        # decoded = base64.decodebytes(buf)
        # decoded = decoded[4:]  # skip the decoded size
        # if return_file_header:
        #     return zlib.decompress(decoded), None
        # else:
        #     return zlib.decompress(decoded)
    elif compression_type == "zstd":
        if zstandard is None:
            raise RuntimeError(
                "zstd is required for decompressing this replay"
            )
        reader = zstandard.ZstdDecompressor().stream_reader(buf)
        data = reader.read()
        return data, header


def _replay_header_parser(game_header: dict, file_header: dict):
    launched_at = file_header["launched_at"]
    title = file_header["title"]
    game_type = ensure_str(file_header["game_type"])
    map_file = ensure_str(game_header["map_file"])
    map_file = map_file.strip("/")[-1]
    players = []
    for army_id, player in game_header["armies"].items():
        if not player["Human"]:
            continue
        nickname = ensure_str(player["PlayerName"])
        clan = player.get("PlayerClan")
        players.append(ReplayPlayerMetadata(
            nickname=nickname,
            player_id=ensure_str(player["OwnerID"]),
            country=ensure_str(player.get("Country")),
            faction=int(player["Faction"]),
            rating_mean=player["MEAN"],
            rating_std=player["DEV"],
            clan=ensure_str(clan if clan else ""),
            team=int(player["Team"]),
            rating=game_header["scenario"]["Options"]["Ratings"][nickname],
        ))
    return title, launched_at, map_file, players, game_type


def _replay_body_parser(replay):
    current_tick = 0
    current_time = timedelta()
    first_message_sent_at = {}
    chat_messages, notifications, resource_transfer = [], [], []
    for cmd in replay["body"]["commands"]:
        if cmd["name"] == "LuaSimCallback" and cmd.get("func") == "GiveResourcesToPlayer":
            args = cmd.get("args", {})
            mass, energy = args.get("Mass", 0.0), args.get("Energy", 0.0)
            message = args.get("Msg", {}).get("text", b'').decode()
            is_chat = args.get("Msg", {}).get("Chat", None)
            player = args.get("Sender", b'').decode()
            message_type = args.get("Msg", {}).get("to", b'').decode()
            target_player = args.get("To")

            # Skipping duplicates
            msg_fingerprint = player + str(message)
            if (msg_fingerprint not in first_message_sent_at or
                    first_message_sent_at[msg_fingerprint] - current_tick > MSG_TICK_TIMEOUT):
                first_message_sent_at[msg_fingerprint] = current_tick
            else:
                continue
            if is_chat:
                if message_type == MessageTypes.auto_notify:
                    # Handling only completion notifications
                    # (such as commander and factory upgrades, experimental and arty completion)
                    if MSG_DONE_SUFFIX in message:
                        if MSG_DONE_SUFFIX2 in message:
                            completed = message[:message.find(MSG_DONE_SUFFIX2)]
                        else:
                            completed = message[:message.find(MSG_DONE_SUFFIX)]
                        completed = completed.strip()
                        msg = CompletionNotification(
                            player=player,
                            completed=completed,
                            sent_at_sec=current_time.total_seconds())
                        notifications.append(msg)
                else:
                    msg = ChatMessage(
                        ally_only=message_type == MessageTypes.allies,
                        player=player,
                        message=message,
                        sent_at_sec=current_time.total_seconds())
                    chat_messages.append(msg)
            else:
                msg = ResourceSent(
                    from_player=player, to_player=target_player,
                    mass=mass, energy=energy,
                    sent_at_sec=current_time.total_seconds())
                resource_transfer.append(msg)
        if cmd["name"] == "Advance":
            current_tick += cmd["ticks"]
            current_time = timedelta(milliseconds=current_tick * 100)
    return chat_messages, notifications, resource_transfer, current_time.seconds


def parse_replay(data_stream, replay_id: str):
    parser = Parser(
        commands=all_commands,
        save_commands=True,
        limit=None,
        stop_on_desync=False
    )

    data, file_header = extract_scfa(data_stream)
    replay = parser.parse(data)
    desync = bool(replay["body"]["sim"]["desync_ticks"])
    chat_messages, notifications, resource_transfer, duration = _replay_body_parser(replay)
    title, launched_at, map_file, players, game_type = _replay_header_parser(
        game_header=replay["header"],
        file_header=file_header
    )
    return ReplayMetadata(
        title=title,
        chat_messages=chat_messages,
        notifications=notifications,
        duration=duration,
        desync=desync,
        players=players,
        game_type=game_type,
        replay_id=replay_id,
        resource_transfer=resource_transfer,
        launched_at_ts=launched_at,
        map=map_file
    )


if __name__ == "__main__":
    f1 = "21708997.fafreplay"
    f2 = "21708990.fafreplay"
    f3 = "21708992.fafreplay"
    with open(f"../data/replays/{f1}", "rb") as f:
        metadata = parse_replay(f, f1)
    print(metadata)
