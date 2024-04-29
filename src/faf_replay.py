import json
from io import FileIO

from fafreplay import extract_scfa
from replay_parser.body import ReplayBody
from replay_parser.constants import CommandStates
from replay_parser.header import ReplayHeader
from replay_parser.reader import ReplayReader

from replay_parser.replay import continuous_parse, parse

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
                    pass
                    # print(current_time, player, message)
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
    print("Game time:", timedelta(milliseconds=replay["body"]["sim"]["tick"] * 100))


def read_replay(data_stream, compressed: bool = True):
    parser = Parser(
        commands=all_commands,
        save_commands=True,
        limit=None,
        stop_on_desync=False
    )

    if compressed:
        data = extract_scfa(data_stream)
    else:
        data = data_stream.read()

    replay = parser.parse(data)
    if replay["body"]["sim"]["desync_ticks"]:
        print("Replay desynced!")
    return replay["header"], _replay_body_parser(replay)


# def read_replay2(filename: str):
#     with open(filename, "rb") as f:
#         decoded_data = extract_scfa(f)
#     reader = ReplayReader(decoded_data)
#     header = ReplayHeader(reader)
#     print(header)
#     for tick, cmd_type, data in ReplayBody(reader).continuous_parse():
#         print(tick, cmd_type, data)
#         if cmd_type == CommandStates.DestroyEntity:
#             print(data)


if __name__ == "__main__":
    f1 = "22233410.fafreplay"
    f2 = "22235042.fafreplay"
    with open(f"C:/Users/gluko/Downloads/{f2}", "rb") as f:
        metadata, msgs = read_replay(f)
    print(metadata)
