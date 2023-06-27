import discord
from discord.ext import commands, tasks
import requests
import asyncio
def convert_seconds(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes} minutes, {seconds} seconds"
bot = commands.Bot(command_prefix='!',intents=discord.Intents.all())

tracked_users = {
    'player name 1': {
        'tag': '',
        'puuid': '' , # you can leave this blank
        'last_match_id': ''# you can leave this blank
    },
    'player name 2': {
        'tag': '',
        'puuid': '',# you can leave this blank
        'last_match_id': ''# you can leave this blank
    },
    'player name 3':{
        'tag': '',
        'puuid': '',# you can leave this blank
        'last_match_id': ''# you can leave this blank
    }
}

match_ids =[]# you can leave this blank

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await get_puuids()

async def get_puuids():
 while 1 != 0:
    for username, data in tracked_users.items():
        username_data = requests.get(f'https://api.henrikdev.xyz/valorant/v1/account/{username}/{data["tag"]}').json()
        puuid = username_data['data']['puuid']
        if puuid != data['puuid']:
            tracked_users[username]['puuid'] = puuid
            await send_valorant_update(username, puuid)
    await asyncio.sleep(360) # waits 360 seconds to prevent api spam, and unrealistic for a game to be done in less than 5

async def send_valorant_update(username, puuid):
    global match_ids

    latest_match = requests.get(f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/eu/{puuid}?size=1").json()
    match_data = latest_match['data'][0]
    match_id = match_data['metadata']['matchid']
    if match_id not in match_ids:
        metadata = match_data['metadata']
        players = match_data['players']['all_players']
        

        map_name = metadata['map']
        game_length = convert_seconds(metadata['game_length'])
        rounds_played = metadata['rounds_played']
        mode = metadata['mode']
        queue = metadata['queue']
        dateplay = metadata['game_start_patched']
        cluster = metadata['cluster']
        match_ids.append(match_id)

        embed = discord.Embed(title=f"{username}'s Match ", description=f"Map: {map_name}", color=discord.Color.blue())
        embed.add_field(name="Game Length", value=game_length, inline=True)
        embed.add_field(name="Rounds Played", value=rounds_played, inline=True)
        embed.add_field(name="Mode", value=mode, inline=True)
        embed.add_field(name="Queue", value=queue, inline=True)
        embed.add_field(name="Server", value=cluster, inline=True)
        embed.set_footer(text=f"MatchID • {match_id} • {dateplay}")

        blue_team_desc = ""
        red_team_desc = ""

        for player in players:
            name = player['name']
            tag = player['tag']
            character = player['character']
            kda = f"{player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}"

            if player['team'] == "Blue":
                blue_team_desc += f"- {name}#{tag} as {character} - {kda}\n"
            elif player['team'] == "Red":
                red_team_desc += f"- {name}#{tag} as {character} - {kda}\n"

        embed.add_field(name="Blue Team", value=blue_team_desc, inline=False)
        embed.add_field(name="Red Team", value=red_team_desc, inline=False)

        channel = bot.get_channel('CHANNEL ID HERE')
        await channel.send(embed=embed)

bot.run('YOUR TOKEN HERE') 
