import discord
from discord.ext import commands, tasks
import requests
import asyncio
import json
import os

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
tracked_users_file = "tracked_users.json"
tracked_matches_file = "tracked_matches.json"

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
            print(e)


async def get_puuids():
    print("Getting puuids")
    try:
        for username, data in tracked_users.items():
            username_data = requests.get(f'https://api.henrikdev.xyz/valorant/v1/account/{username}/{data["tag"]}').json()
            puuid = username_data['data']['puuid']
            if puuid != data['puuid']:
                tracked_users[username]['puuid'] = puuid
            await send_valorant_update(username, puuid)
    except Exception as e:
        print(e)


async def send_valorant_update(username, puuid):
    print("Send function running")
    global tracked_matches
    try:
        latest_match = requests.get(f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/eu/{puuid}?size=1").json()
        match_data = latest_match['data'][0]
        match_id = match_data['metadata']['matchid']
        if match_id not in tracked_matches:
            metadata = match_data['metadata']
            players = match_data['players']['all_players']

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

                if mode == "competitive":
                    rank = player['currenttier_patched']
                    if player['team'] == "Blue":
                        blue_team_desc += f"- {rank} {name}#{tag} as {character} - K/D/A: {kda}\n"
                    elif player['team'] == "Red":
                        red_team_desc += f"- {rank} {name}#{tag} as {character} - K/D/A: {kda}\n"
                else:
                    if player['team'] == "Blue":
                        blue_team_desc += f"- {name}#{tag} as {character} - K/D/A: {kda}\n"
                    elif player['team'] == "Red":
                        red_team_desc += f"- {name}#{tag} as {character} - K/D/A: {kda}\n"

            embed.add_field(name=f"Blue Team - {blue_score}", value=blue_team_desc, inline=False)
            embed.add_field(name=f"Red Team - {red_score}", value=red_team_desc, inline=False)

            channel_id = 1234567890  # Replace with your desired channel ID
            channel = bot.get_channel(channel_id)
            await channel.send(embed=embed)
            tracked_matches.append(match_id)
            with open(tracked_matches_file, "w") as f:
                json.dump(tracked_matches, f)
    except Exception as e:
        print(e)
        channel_id = 1234567890  # Replace with your desired channel ID
        channel = bot.get_channel(channel_id)
        await channel.send(e)

bot.run('YOUR TOKEN HERE')
