import base64
import json
import zlib
from dataclasses import dataclass

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


MSG_TICK_TIMEOUT = 20  # for deduplication
MSG_DONE_SUFFIX = "done!"
MSG_DONE_SUFFIX2 = "construction done!"


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


@dataclass
class ParsedReplayData:
    header: dict
    chat_messages: list[ChatMessage]
    notifications: list[CompletionNotification]
    duration: float
    desync: bool


def extract_scfa(fobj, return_file_header: bool = False):
    """extract_scfa(fobj: io.BytesIO) -> bytes

    Turns data from `.fafreplay` format into `.scfareplay` format. The zstd
    library needs to be installed in order to decode version 2 of the
    `.fafreplay` format.
    """
    header = json.loads(fobj.readline().decode())
    buf = fobj.read()
    compression_type = header.get("compression")

    if compression_type == "zlib":
        raise Exception("Cannot decode  zstd compression type")
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
        if return_file_header:
            return data, header
        else:
            return data


def parse_replay(data_stream, compressed: bool = True):
    parser = Parser(
        commands=all_commands,
        save_commands=True,
        limit=None,
        stop_on_desync=False
    )

    if compressed:
        data, file_header = extract_scfa(data_stream, return_file_header=True)
    else:
        raise Exception("Unsupported compression format")

    replay = parser.parse(data)
    desync = bool(replay["body"]["sim"]["desync_ticks"])
    chat_messages, notifications, resource_transfer, duration = _replay_body_parser(replay)
    return ParsedReplayData(
        header=replay["header"] | file_header,
        chat_messages=chat_messages,
        notifications=notifications,
        duration=duration,
        desync=desync
    )


if __name__ == "__main__":
    f1 = "21708997.fafreplay"
    f2 = "21708990.fafreplay"
    f3 = "21708992.fafreplay"
    with open(f"../data/replays/{f1}", "rb") as f:
        data = parse_replay(f)
    print(data)
