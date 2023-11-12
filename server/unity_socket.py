""" Used to manipulate socket connection """
from typing import TYPE_CHECKING
import socket
import dataclasses
import time
import logging
import os
import asyncio
import requests
import srcomapi
import srcomapi.datatypes as dt
from trail_timer import TrailTimer
from tokens import STEAM_API_KEY

if TYPE_CHECKING: # for imports with intellisense
    from unity_socket_server import UnitySocketServer

script_path = os.path.dirname(os.path.realpath(__file__))

operations = {
    "STEAM_ID":
        lambda netPlayer, data: netPlayer.set_steam_id(str(data[1])),
    "STEAM_NAME":
        lambda netPlayer, data: netPlayer.set_steam_name(data[1]),
    "WORLD_NAME":
        lambda netPlayer, data: netPlayer.set_world_name(data[1]),
    "BOUNDRY_ENTER":
        lambda netPlayer, data: netPlayer.on_boundry_enter(data[1], data[2]),
    "BOUNDRY_EXIT":
        lambda netPlayer, data: netPlayer.on_boundry_exit(data[1], data[2]),
    "CHECKPOINT_ENTER":
        lambda netPlayer, data: netPlayer.on_checkpoint_enter(
            data[1],
            data[2],
            int(data[3]),
            float(data[4])
        ),
    "RESPAWN":
        lambda netPlayer, data: netPlayer.on_respawn(),
    "MAP_ENTER":
        lambda netPlayer, data: netPlayer.on_map_enter(data[2]), # WARNING: data[2] FOR A REASON
    "MAP_EXIT":
        lambda netPlayer, data: netPlayer.on_map_exit(),
    "BIKE_SWITCH":
        lambda netPlayer, data: netPlayer.on_bike_switch(data[2]), # WARNING: data[2] FOR A REASON
    "REP":
        lambda netPlayer, data: netPlayer.set_reputation(data[1]),
    "SPEEDRUN_DOT_COM_LEADERBOARD":
        lambda netPlayer, data: (
            netPlayer.send(
                "SPEEDRUN_DOT_COM_LEADERBOARD|"
                + data[1] + "|"
                + str(netPlayer.convert_to_unity(
                    netPlayer.get_speedrun_dot_com_leaderboard(data[1])
                ))
            )
        ),
    "LEADERBOARD":
        lambda netPlayer, data: (
            netPlayer.send(
                "LEADERBOARD|"
                + data[1] + "|"
                + str(
                    netPlayer.get_leaderboard(data[1])
                )
            )
        ),
    "CHAT_MESSAGE":
        lambda netPlayer, data: netPlayer.send_chat_message(data[1]),
    "START_SPEED":
        lambda netPlayer, data: netPlayer.start_speed(float(data[1])),
    "TRICK":
        lambda netPlayer, data: netPlayer.set_last_trick(str(data[1])),
    "VERSION":
        lambda netPlayer, data: netPlayer.set_version(str(data[1])),
    "GET_MEDALS":
        lambda netPlayer, data: netPlayer.get_medals(str(data[1])),
    "LOG_LINE":
        lambda netPlayer, data: netPlayer.log_line(data[1:]),
}


@dataclasses.dataclass
class Player:
    """ Class to hold instance data of a descenders player """
    steam_name: str
    avatar_src: str
    steam_id: str
    bike_type: str
    world_name: str
    last_trick: str
    reputation: int
    version: str
    time_started: float

class UnitySocket():
    """ Used to handle the connection to the descenders unity client """
    def __init__(self, conn: socket.socket, addr, parent: 'UnitySocketServer'):
        logging.info(
            "%s- New Instance created", addr
        )
        self.addr = addr
        self.conn = conn
        self.parent = parent
        self.dbms = parent.dbms
        self.trails = {}
        self.info: Player = Player(
            steam_name="", steam_id="",
            avatar_src="",
            bike_type="", world_name="",
            last_trick="", reputation=0,
            version="OUTDATED", time_started=time.time()
        )
        self.send("SUCCESS")

    def log_line(self, line):
        """ Log a line of data to a text file for a specific Steam user. """
        line = "|".join(line)
        with open(
            f"{os.getcwd()}/output_logs/{self.info.steam_id}.txt","a+",
            encoding="utf-8"
        ) as file:
            file.write(f"{round(time.time())} - {line}\n")

    def send_chat_message(self, mess: str):
        """ Send a chat message to all players in the same session """
        logging.info(
            "%s '%s'\t- sending chat message '%s'",
            self.info.steam_id, self.info.steam_name, mess
        )
        for player in self.parent.players:
            player.send(f"CHAT_MESSAGE|{self.info.steam_name}|{self.info.world_name}|{mess}")

    def set_last_trick(self, trick: str):
        """ Set the last performed trick for a player """
        logging.info(
            "%s '%s'\t- last_trick is %s",
            self.info.steam_id,self.info.steam_name,trick
        )
        self.info.last_trick = trick

    def set_version(self, version: str):
        """ Set the version of a player's software or application. """
        logging.info(
            "%s '%s'\t- on version %s", self.info.steam_id, self.info.steam_name, version
        )
        self.info.version = version

    def set_text_colour(self, r: int, g: int, b: int):
        """ Set the text color for a chat message. """
        self.send(f"SET_TEXT_COLOUR|{r}|{g}|{b}")

    def set_text_default(self):
        """ Reset the text color to the default for chat messages """
        self.send("SET_TEXT_COL_DEFAULT")

    def set_reputation(self, reputation):
        """ Set the reputation value for a player """
        logging.info(
            "%s '%s'\t- reputation is %s", self.info.steam_id,
            self.info.steam_name, reputation
        )
        try:
            self.info.reputation = int(reputation)
        except ValueError:
            pass

    def start_speed(self, starting_speed: float):
        """ Set the starting speed for a player and invalidate timers if necessary """
        logging.info(
            "%s '%s'\t- start speed is %s",
            self.info.steam_id, self.info.steam_name, starting_speed
        )
        for trail_name, trail in self.trails.items():
            trail.starting_speed = starting_speed
            if starting_speed > self.dbms.max_start_time(trail_name):
                trail.invalidate_timer(
                    "You went through the start too fast!"
                )

    def convert_to_unity(self, leaderboard):
        """ Convert a leaderboard data structure to a Unity-friendly format. """
        if len(leaderboard) == 0:
            return {}
        keys = [key for key in leaderboard[0]]
        unity_leaderboard = {}
        for key in keys:
            unity_leaderboard[key] = []
        for leaderboard_time in leaderboard:
            for key in leaderboard_time:
                unity_leaderboard[key].append(leaderboard_time[key])
        return unity_leaderboard

    def get_leaderboard(self, trail_name):
        """
        Get and convert the leaderboard data for a specific trail to a Unity-friendly format.
        """
        return self.convert_to_unity(
            [
                {
                    "place": leaderboard["place"],
                    "time": leaderboard["time"],
                    "name": leaderboard["name"],
                    "pen": float(leaderboard["penalty"]),
                    "bike": leaderboard["bike"],
                    "verified": leaderboard["verified"],
                }
                for leaderboard in self.dbms.get_leaderboard(
                    trail_name, steam_id=self.info.steam_id
                )
            ]
        )

    def get_speedrun_dot_com_leaderboard(self, trail_name):
        """ Retrieve the leaderboard data for a specific trail from Speedrun.com """
        api = srcomapi.SpeedrunCom()
        game = api.get_game("Descenders")
        for level in game.levels:
            if level.data["name"] == trail_name:
                leaderboard = dt.Leaderboard(
                    api,
                    data=api.get(
                        f"leaderboards/{game.id}/level/{level.id}"
                        f"/7dg4yg4d?embed=variables"
                    )
                )
                leaderboard_json = ([
                    {
                        "place": leaderboard["place"],
                        "time": leaderboard["run"].times["realtime_t"],
                        "name": leaderboard["run"].players[0].name
                    } for leaderboard in leaderboard.runs if (
                        leaderboard["place"] != 0
                    )
                    ])
                return leaderboard_json
        return [{"place": 1, "time": 0, "name": "No times", "verified": "1", "pen": 0}]

    def get_total_time(self, on_world=False):
        """
        Get the total time spent by a player in the game, optionally within a specific world.
        """
        if on_world:
            return self.dbms.get_time_on_world(self.info.steam_id, self.info.world_name)
        return self.dbms.get_time_on_world(self.info.steam_id)

    def get_avatar_src(self):
        """ Get the URL of the player's avatar image. """
        if self.info.avatar_src is not None:
            return self.info.avatar_src
        avatar_src_req = requests.get(
            "https://api.steampowered.com/"
            "ISteamUser/GetPlayerSummaries"
            f"/v0002/?key={STEAM_API_KEY}"
            f"&steamids={self.info.steam_id}", timeout=10
        )
        try:
            self.info.avatar_src = avatar_src_req.json()[
                "response"]["players"][0]["avatarfull"]
        except (IndexError, KeyError):
            self.info.avatar_src = self.dbms.get_avatar(self.info.steam_id)
        return self.info.avatar_src

    def set_steam_name(self, steam_name):
        """ Set the steam name of a player and invalidate timers if necessary """
        logging.info(
            "%s '%s'\t- steam name setting to %s", self.info.steam_id,
            self.info.steam_name, steam_name
        )
        self.info.steam_name = steam_name
        if self.info.steam_id is not None:
            self.has_both_steam_name_and_id()

    def ban(self, _type: str):
        """ Ban a player from the game. """
        logging.info(
            "%s '%s'\t- banned with type %s",
            self.info.steam_id, self.info.steam_name, _type
        )
        if _type == "ILLEGAL":
            self.send("TOGGLE_GOD")
        self.send("BANNED|" + _type)

    def has_both_steam_name_and_id(self):
        """ Called when a player has both a steam name and id. """
        self.dbms.submit_alias(self.info.steam_id, self.info.steam_name)
        for player in self.parent.players:
            if (
                player.info.steam_id == self.info.steam_id
                and self is not player
            ):
                logging.warning(
                    "%s '%s'\t- duplicate steam id!",
                    self.info.steam_id, self.info.steam_name
                )
                self.parent.players.remove(player)
                del player
        if self.info.steam_id == "OFFLINE" or self.info.steam_id == "":
            self.send("TOGGLE_GOD")
        banned_names = ["descender", "goldberg", "skidrow", "player"]
        for banned_name in banned_names:
            if self.info.steam_name.lower() == banned_name:
                self.ban("ILLEGAL")
        ban_type = self.dbms.get_ban_status(self.info.steam_id)
        if ban_type == "CLOSE":
            self.ban("CLOSE")
        elif ban_type == "CRASH":
            self.ban("CRASH")
        elif ban_type == "ILLEGAL":
            self.ban("ILLEGAL")

    def set_steam_id(self, steam_id : str):
        """ Set the steam id of a player and invalidate timers if necessary """
        logging.info(
            "%s '%s'\t- steam id set to %s", self.info.steam_id,
            self.info.steam_name, steam_id
        )
        self.info.steam_id = steam_id
        if self.info.steam_name is not None:
            self.has_both_steam_name_and_id()

    def get_default_bike(self):
        """ Get the default bike for a player. """
        if self.info.world_name is not None:
            start_bike = self.dbms.get_start_bike(self.info.world_name)
            if start_bike is None:
                return "enduro"
            return start_bike
        else:
            return "enduro"

    def set_world_name(self, world_name):
        """ Set the world name of a player and invalidate timers if necessary """
        logging.info(
            "%s '%s'\t- set world name to '%s'", self.info.steam_id,
            self.info.steam_name, world_name
        )
        self.info.world_name = world_name
        self.dbms.update_player(
            self.info.steam_id,
            self.info.steam_name,
            self.get_avatar_src()
        )
        self.dbms.submit_ip(self.info.steam_id, self.addr[0], self.addr[1])

    def send(self, data: str):
        """ Send data to the descenders unity client """
        logging.info(
            "%s '%s'\t- sending data '%s'", self.info.steam_id, self.info.steam_name, data
        )
        try:
            self.conn.sendall((data + "\n").encode())
        except OSError:
            pass

    def send_all(self, data: str):
        """ Send data to all players in the same session """
        logging.info(
            "%s '%s'\t- sending to all the data '%s''", self.info.steam_id,
            self.info.steam_name, data
        )
        for player in self.parent.players:
            player.send(data)

    def handle_data(self, data: str):
        """ Handle data sent from the descenders unity client """
        if data == "":
            return
        data_list = data.split("|")
        for operator, function in operations.items():
            if data.startswith(operator):
                function(self, data_list)

    def recieve(self):
        """ Recieve data from the descenders unity client """
        while True:
            if time.time()-self.info.time_started > 20 and self.info.steam_id == "":
                logging.info(
                    "%s- failed to give steam id in time, timed out automatically", self.addr
                )
                self.conn.close()
                break
            try:
                data = self.conn.recv(8192)
                if not data: # if data is finished
                    break
                try:
                    for piece in data.decode().split("\n"):
                        self.handle_data(piece)
                except UnicodeDecodeError:
                    pass
            except ConnectionResetError:
                break
            except OSError:
                pass
            except Exception as e:
                logging.error("PLAYER WILL BE DELETED! Error in recieve loop: %s", e)
                break

    def invalidate_all_trails(self, reason: str):
        """ Invalidate all trails for a player. """
        logging.info(
            "%s '%s'\t- all trails invalidated due to '%s'",
            self.info.steam_id, self.info.steam_name, reason
        )
        for trail_name, trail in self.trails.items():
            if trail_name in self.trails:
                trail.invalidate_timer(reason)

    def on_respawn(self):
        """ Called when a player respawns """
        logging.info("%s '%s'\t- respawned", self.info.steam_id, self.info.steam_name)
        self.invalidate_all_trails("Respawn/death Detected")

    def get_trail(self, trail_name) -> TrailTimer:
        """ Get a trail timer for a player. """
        if trail_name not in self.trails:
            self.trails[trail_name] = TrailTimer(trail_name, self)
        return self.trails[trail_name]

    def on_bike_switch(self, new_bike: str):
        """ Called when a player switches bikes."""
        self.info.bike_type = new_bike
        #self.send_all(f"SET_BIKE|{self.bike_type}|{self.info.steam_id}")
        self.invalidate_all_trails("You switched bikes!")

    def on_boundry_enter(self, trail_name: str, boundry_guid: str):
        """ Called when a player enters a boundry. """
        trail = self.get_trail(trail_name)
        trail.add_boundary(boundry_guid)

    def on_boundry_exit(self, trail_name: str, boundry_guid: str):
        """ Called when a player exits a boundry. """
        trail = self.get_trail(trail_name)
        trail.remove_boundary(boundry_guid)

    def on_checkpoint_enter(
        self,
        trail_name: str,
        checkpoint_type: str,
        total_checkpoints: int,
        client_time: float
    ):
        """ Called when a player enters a checkpoint. """
        logging.info(
            "%s '%s'\t- entered checkpoint on trail '%s' of type '%s'",
            self.info.steam_id, self.info.steam_name,
            trail_name, checkpoint_type
        )
        self.get_trail(trail_name).total_checkpoints = int(total_checkpoints)
        if checkpoint_type == "Start":
            self.get_trail(trail_name).start_timer(total_checkpoints)
        if checkpoint_type == "Intermediate":
            self.get_trail(trail_name).checkpoint(client_time)
        if checkpoint_type == "Finish":
            self.get_trail(trail_name).end_timer(client_time)

    def on_map_enter(self, map_name: str):
        """ Called when a player enters a map. """
        self.info.world_name = map_name
        self.info.time_started = time.time()
        self.update_concurrent_users()
        if (self.info.bike_type == "" or self.info.bike_type is None):
            self.info.bike_type = self.get_default_bike()
        if self.info.steam_id is not None:
            self.send_all("SET_BIKE|" + self.info.bike_type + "|" + self.info.steam_id)

    def on_map_exit(self):
        """ Called when a player exits a map. """
        self.update_concurrent_users()
        for trail_name, trail in self.trails.items():
            if trail_name in self.trails:
                trail.invalidate_time()
        self.trails = {}
        self.dbms.end_session(
            self.info.steam_id,
            self.info.time_started,
            time.time(),
            self.info.world_name
        )
        self.conn.close()

    def update_concurrent_users(self):
        """ Update the discord bot's presence with the number of concurrent users. """
        discord_bot = self.parent.discord_bot
        if discord_bot is None:
            logging.info("tried to update users before discord bot was created")
        try:
            if discord_bot is not None:
                asyncio.run(discord_bot.set_presence(
                        str(len(self.parent.players))
                        + " concurrent users!"
                ))
        except RuntimeError:
            logging.info("update_concurrent_users() called, but it's already being attempted")

    def get_medals(self, trail_name: str):
        """ Get the medals for a player on a specific trail. """
        logging.info(
            "%s '%s'\t- fetched medals on trail '%s'",
            self.info.steam_id, self.info.steam_name, trail_name
        )
        (rainbow, gold, silver, bronze) = self.dbms.get_medals(
            self.info.steam_id,
            trail_name
        )
        self.send(f"SET_MEDAL|{trail_name}|{rainbow}|{gold}|{silver}|{bronze}")
