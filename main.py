import discord
from discord.ext import commands, tasks
import requests



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

last_global_match_id = ''# you can leave this blank

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    get_puuids.start()

@tasks.loop(minutes=5)  # you can change this if you want, would not advise values less than 2 minutes.
async def get_puuids():
    for username, data in tracked_users.items():
        username_data = requests.get(f'https://api.henrikdev.xyz/valorant/v1/account/{username}/{data["tag"]}').json()
        puuid = username_data['data']['puuid']
        if puuid != data['puuid']:
            tracked_users[username]['puuid'] = puuid
            await send_valorant_update(username, puuid)

async def send_valorant_update(username, puuid):
    global last_global_match_id

    latest_match = requests.get(f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/eu/{puuid}?size=1").json()
    match_data = latest_match['data'][0]
    match_id = match_data['metadata']['matchid']
    if match_id != last_global_match_id:
        last_global_match_id = match_id
        tracked_users[username]['last_match_id'] = match_id
        metadata = match_data['metadata']
        players = match_data['players']['all_players']

        map_name = metadata['map']
        game_length = convert_seconds(metadata['game_length'])
        rounds_played = metadata['rounds_played']
        mode = metadata['mode']
        queue = metadata['queue']
        matchid = metadata['matchid']
        dateplay = metadata['game_start_patched']
        cluster = metadata['cluster']

        embed = discord.Embed(title="Valorant Match Update", description=f"Map: {map_name}", color=discord.Color.blue())
        embed.add_field(name="Game Length", value=game_length, inline=True)
        embed.add_field(name="Rounds Played", value=rounds_played, inline=True)
        embed.add_field(name="Mode", value=mode, inline=True)
        embed.add_field(name="Queue", value=queue, inline=True)
        embed.add_field(name="Server", value=cluster, inline=True)
        embed.set_footer(text=f"MatchID • {matchid} • {dateplay}")

        blue_team_desc = ""
        red_team_desc = ""

        for player in players:
            name = player['name']
            tag = player['tag']
            character = player['character']
            kda = f"{player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}"

            if player['team'] == "Blue":
                blue_team_desc += f"- {name}#{tag} as {character}, K/D/A: {kda}\n"
            elif player['team'] == "Red":
                red_team_desc += f"- {name}#{tag} as {character}, K/D/A: {kda}\n"

        embed.add_field(name="Blue Team", value=blue_team_desc, inline=False)
        embed.add_field(name="Red Team", value=red_team_desc, inline=False)

        channel = bot.get_channel('CHANNEL ID HERE')
        await channel.send(embed=embed)

bot.run('YOUR TOKEN HERE') 
