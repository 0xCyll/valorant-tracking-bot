import discord
from discord.ext import commands, tasks
import requests
import asyncio
import json
import subprocess
import os
import traceback
import sys

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
tracked_users_file = "tracked_users.json"
tracked_matches_file = "tracked_matches.json"
ChannelID = "channelidhere" # the channel id you want your games to be sent in
tracked_users = {}
tracked_matches = []

if os.path.exists(tracked_users_file):
    with open(tracked_users_file, "r") as f:
        tracked_users = json.load(f)

if os.path.exists(tracked_matches_file):
    with open(tracked_matches_file, "r") as f:
        tracked_matches = json.load(f)


def convert_seconds(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes} minutes, {seconds} seconds"


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    while True:
        try:
            await get_puuids()
            await asyncio.sleep(50)  # Wait 50 seconds to prevent API spam and allow realistic game durations
        except Exception as e:
            print(traceback.format_exc())
   


async def get_puuids():
    print("Getting puuids")
    try:
        for username, data in tracked_users.items():
            username_data = None  
            if 'puuid' in data and data['puuid']:
                puuid = data['puuid']
            else:
                username_data = requests.get(f'https://api.henrikdev.xyz/valorant/v1/account/{username}/{data["tag"]}').json()
                puuid = username_data['data']['puuid']
                tracked_users[username]['puuid'] = puuid
                with open(tracked_users_file, "w") as f:
                    json.dump(tracked_users, f)
            if puuid != data['puuid']:
                tracked_users[username]['puuid'] = puuid
                with open(tracked_users_file, "w") as f:
                    json.dump(tracked_users, f)
            if username_data and 'name' in username_data['data'] and username != username_data['data']['name']:
                tracked_users[username]['name'] = username_data['data']['name']
                with open(tracked_users_file, "w") as f:
                    json.dump(tracked_users, f)
            if username_data and 'tag' in username_data['data'] and data['tag'] != username_data['data']['tag']:
                tracked_users[username]['tag'] = username_data['data']['tag']
                with open(tracked_users_file, "w") as f:
                    json.dump(tracked_users, f)
            await send_valorant_update(username, puuid)
    except Exception as e:
        print(traceback.format_exc())



async def send_valorant_update(username, puuid):
    global tracked_matches
    try:
        latest_match = requests.get(f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/eu/{puuid}?size=1").json()
        match_data = latest_match['data'][0]
        match_id = match_data['metadata']['matchid']
        if match_id not in tracked_matches:
            print("Send function running")
            metadata = match_data['metadata']
            players = match_data['players']['all_players']
            tracked_matches.append(match_id)
            with open(tracked_matches_file, "w") as f:
                json.dump(tracked_matches, f)
            map_name = metadata['map']
            game_length = convert_seconds(metadata['game_length'])
            rounds_played = metadata['rounds_played']
            mode = metadata['mode']
            date_played = metadata['game_start_patched']
            cluster = metadata['cluster']
            tracked_users[username]['last_match_id'] = match_id

            embed = discord.Embed(title=f"{username}'s Match", description=f"Map: {map_name}", color=discord.Color.blue())
            embed.add_field(name="Game Length", value=game_length, inline=True)
            embed.add_field(name="Rounds Played", value=rounds_played, inline=True)
            embed.add_field(name="Mode", value=mode, inline=True)
            embed.add_field(name="Server", value=cluster, inline=True)
            embed.set_footer(text=f"MatchID • {match_id} • {date_played}")
            red_score = match_data['teams']['red']['rounds_won']
            blue_score = match_data['teams']['blue']['rounds_won']

            blue_team_desc = ""
            red_team_desc = ""

            for player in players:
                name = player['name']
                tag = player['tag']
                character = player['character']
                kda = f"{player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}"

                if mode == "Competitive":
                    rank = player['currenttier_patched']
                    if player['team'] == "Blue":
                        blue_team_desc += f"- {rank} {name}#{tag} as {character} - K/D/A: {kda}\n"
                    elif player['team'] == "Red":
                        red_team_desc += f"- {rank} {name}#{tag} as {character} - K/D/A: {kda}\n"
                elif mode == "Deathmatch":
                    blue_team_desc += f"- {name}#{tag} as {character} - K/D/A: {kda}\n"
                else:
                    if player['team'] == "Blue":
                        blue_team_desc += f"- {name}#{tag} as {character} - K/D/A: {kda}\n"
                    elif player['team'] == "Red":
                        red_team_desc += f"- {name}#{tag} as {character} - K/D/A: {kda}\n"
            if mode == "Deathmatch":
                embed.add_field(name=f"Blue Team - {blue_score}", value=blue_team_desc, inline=False)
            else:
                embed.add_field(name=f"Blue Team - {blue_score}", value=blue_team_desc, inline=False)
                embed.add_field(name=f"Red Team - {red_score}", value=red_team_desc, inline=False)

            channel = bot.get_channel(ChannelID)
            await channel.send(embed=embed)
            
    except Exception as e:
        print(traceback.format_exc())




bot.run('Your Token')
