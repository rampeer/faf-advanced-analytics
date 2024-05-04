from dataclasses import dataclass

from fafreplay import extract_scfa
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


def _replay_body_parser(replay):
    current_tick = 0
    current_time = timedelta()
    chat_messages, notifications = [], []
    for cmd in replay["body"]["commands"]:
        if cmd["name"] == "LuaSimCallback" and cmd.get("func") == "GiveResourcesToPlayer":
            args = cmd.get("args", {})
            mass, energy = args.get("Mass", 0.0), args.get("Energy", 0.0)
            message = args.get("Msg", {}).get("text", b'').decode()
            is_chat = args.get("Msg", {}).get("Chat", None)
            player = args.get("Sender", b'').decode()
            message_type = args.get("Msg", {}).get("to", b'').decode()
            target_player = args.get("To")
            if is_chat:
                if message_type == MessageTypes.auto_notify:
                    continue
                    # print(current_time, player, message)
                else:
                    pass
                    # chat_messages.append()
                # print("Chat message")
                # print(current_time, player, mass, energy, message, message_type, target_player)
            else:
                pass
                # print("Sending resources")
        elif cmd["name"] == "LuaSimCallback":
            # print(cmd)
            pass
        # elif cmd["name"] == commands.CreateUnit:
        #     print(cmd)
        if cmd["name"] == "Advance":
            current_tick += cmd["ticks"]
            current_time = timedelta(milliseconds=current_tick * 100)
    return chat_messages, notifications, current_time.seconds


@dataclass
class ParsedReplayData:
    header: dict
    chat_messages: list
    notifications: list
    duration: float
    desync: bool


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
    chat_messages, notifications, duration = _replay_body_parser(replay)
    return ParsedReplayData(
        header=replay["header"] | file_header,
        chat_messages=chat_messages,
        notifications=notifications,
        duration=duration,
        desync=desync
    )


if __name__ == "__main__":
    f1 = "22233410.fafreplay"
    f2 = "21708010.fafreplay"
    with open(f"data/replays/{f2}", "rb") as f:
        metadata, msgs = parse_replay(f)
    print(metadata)
