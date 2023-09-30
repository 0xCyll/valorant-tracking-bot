import discord
from discord.ext import commands
import requests
import asyncio
import json
import os
import traceback
import random
import re


LOGGINGCHANNEL= int("ENTER CHANNEL ID FOR ANY ERROR LOGS")
MAINCHANNEL= int("Enter THE CHANNEL ID FOR WHERE YOU WANT YOUR MATCHES TO BE OUTPUTTED")
BOTTOKEN= "ENTER TOKEN OF DISCORD BOT"
REGION = "eu" # eu by default change if you want
## the following region codes are
## eu for europe, 
## br, latam and na(however br and latam will be internally converted to na)
## ap for asia and kr for korea 
class Bot(commands.Bot):
    def __init__(self):
        intents=discord.Intents.default()
        intents.message_content= True
        super().__init__(command_prefix="!", intents=intents,help_command=None)

    async def setup_hook(self):
         await self.tree.sync(guild=None)
         print(f"Synced Slash commands for {self.user}.")


async def name2icon(character_name):
    filename="emoji_list.json"
    emoji_data = {}
    with open(filename, "r") as f:
        emoji_data = json.load(f)
     
    emoji_id = emoji_data.get(character_name)
    if emoji_id is not None:
        return f"<:{character_name}:{emoji_id}>"
    else:
        return character_name.capitalize()



async def logger(message):
    channel = bot.get_channel(LOGGINGCHANNEL)
    await channel.send(message)


bot = Bot()
tracked_users_file = "tracked_users.json"
tracked_matches_file = "tracked_matches.json"

tracked_users = {}
tracked_matches = []
if not os.path.exists("matches"):
    os.mkdir("matches")
if os.path.exists(tracked_users_file):
    with open(tracked_users_file, "r") as f:
        tracked_users = json.load(f)

if os.path.exists(tracked_matches_file):
    with open(tracked_matches_file, "r") as f:
        tracked_matches = json.load(f)


def convert_seconds(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes} minutes, {seconds} seconds"

@bot.hybrid_command(description="View Users currently being tracked for valorant games",with_app_command=True)
async def view_tracked_users(ctx):
    try:
        with open(tracked_users_file, "r") as f:
            tracked_users_data = json.load(f)

        if not tracked_users_data:
            await ctx.send("No users are currently being tracked.")
            return

        tracked_list = "\n".join(tracked_users_data.keys())
        embed=discord.Embed(color=discord.Color.green())
        embed.add_field(name="Currently tracked users",value=tracked_list)
        await ctx.reply(embed=embed)
    except FileNotFoundError:
        await ctx.send("No users are currently being tracked.")
    except Exception as e:
        await ctx.send("An error occurred while trying to view tracked users.")
        await logger(traceback.format_exc())
        


@bot.hybrid_command(description="Add a User to be tracked",with_app_command=True)
async def track_user(ctx, username: str, tag: str):
    global tracked_users
    try:
        safeusername = username.replace(" ", "%20") 
        username_data = requests.get(f'https://api.henrikdev.xyz/valorant/v1/account/{safeusername}/{tag}').json()

        if 'data' in username_data:
            puuid = username_data['data']['puuid']
            region = username_data['data']['region']
            user_key = f"{username}#{tag}"

            if user_key in tracked_users:
                await ctx.send(f"{username}#{tag} is already being tracked.")
            else:
                tracked_users[username] = {'name': username_data['data']['name'], 'tag': tag, 'puuid': puuid}
                with open(tracked_users_file, "w") as f:
                    json.dump(tracked_users, f)
                await ctx.send(f"Successfully added {username}#{tag} in the {region} region to the tracked users.")
                with open(tracked_users_file, "r") as f:
                    tracked_users = json.load(f)
                await get_puuids()
                    
        else:
            if username_data['status'] == "429":
                await logger("api rate limit reached this is expected.")
            await ctx.send("Invalid username and tag. Please provide a valid Valorant username and tag.")
    except Exception as e:
        await logger(traceback.format_exc())
        await ctx.send("An error occurred while processing your request.")

@bot.hybrid_command(name='remove', description="Remove a user from the tracker, input username not tag", with_app_command=True)
async def tracker_remove(ctx, username: str,):

        if username not in tracked_users['username']:
            return await ctx.send('User is not currently being tracked.', ephemeral=True)

        del tracked_users['username']

        await ctx.send(f'Stopped tracking {username}.')



@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Streaming(name=f"Tracking valorant games!", url='https://www.twitch.tv/0xcyll'))
    while True:
        try:
            await get_puuids()
            await asyncio.sleep(180)  # prevent api spam
        except Exception as e:
            await logger(traceback.format_exc())
           


async def get_puuids():
    try:
        for username, data in tracked_users.items():
            username_data = None  
            if 'puuid' in data and data['puuid']:
                puuid = data['puuid']
            else:
                await asyncio.sleep(15)
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
        pass



async def val_rr_gains(puuid,matchid):
    try:
        mmr_view = requests.get(f"https://api.henrikdev.xyz/valorant/v1/by-puuid/lifetime/mmr-history/{REGION}/{puuid}?size=14").json()
        matches = mmr_view["data"]

        for match in matches:
            if match["match_id"] == matchid:
                mmr_change = match["last_mmr_change"]
                if int(mmr_change) > 0:
                    ranker = f"+{mmr_change}"
                else:
                    ranker = mmr_change
                return(ranker)
 
    except Exception as e:
        await logger(traceback.format_exc())


async def send_valorant_update(username, puuid):
    global tracked_matches
    try:
        latest_match = requests.get(f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/{REGION}/{puuid}?size=1").json()
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
            
            filename = os.path.join("matches", str(match_id) + ".json")
            with open(filename, 'w') as file:
                json.dump(latest_match, file)
            party_id_counts = {}




            for player in players:
                party_id = player['party_id']
                if party_id in party_id_counts:
                    party_id_counts[party_id] += 1
                else:
                    party_id_counts[party_id] = 1
            color_codes = ["🔴", "🟢", "🔵", "🟡", "🟣", "🟠"]
            party_id_colors = {}

            for party_id, count in party_id_counts.items():
                if count > 1:
                    party_id_colors[party_id] = random.choice(color_codes)




            embed = discord.Embed(title=f"{username}'s **{mode}** Match on **{map_name}**", color=discord.Color.blue())
            embed.add_field(name="Game Length", value=game_length, inline=True)
            embed.add_field(name="Rounds Played", value=rounds_played, inline=True)
            embed.add_field(name="Server", value=cluster, inline=True)
            embed.set_footer(text=f"MatchID • {match_id} • {date_played}")
            red_score = match_data['teams']['red']['rounds_won']
            blue_score = match_data['teams']['blue']['rounds_won']

            blue_p = []
            red_p = []
            team_p = []

            for player in players:
                party_id = player['party_id']
                party_color = party_id_colors.get(party_id, '')
                puuid1 = player["puuid"]
                name = player['name']
                tag = player['tag']
                level = player['level']
                score = player['stats']['score']
                character = await name2icon(player['character'].replace('/', ''))
                kda = f"{player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}"

                if mode == "Competitive":
                     if blue_score == red_score:
                      winning_team = "Draw"
                     elif blue_score > red_score:
                       winning_team ="Blue"
                     else:
                      winning_team = "Red"
                     mmrchange = await val_rr_gains(puuid1,match_id)
                     if mmrchange == None:
                        mmrchange = "0"
                     rank = player['currenttier_patched']
                     kd_ratio = player['stats']['kills'] / max(player['stats']['deaths'], 1) 
                     if party_color:
                         player_info =f"- **{mmrchange}RR**  -{rank} {character} {party_color} {name} \n {kda}\n"
                     else:
                        player_info = f"- **{mmrchange}RR** -{rank} {character} {name} \n {kda}\n"
                elif mode == "Deathmatch":
                        
                    kd_ratio = player['stats']['kills'] / max(player['stats']['deaths'], 1)
                    if party_color:
                        player_info = f"-  {character} {party_color} {name}  {kda}\n"
                    else:
                        player_info = f"- {character} {name}  {kda}\n"

                else:
                     if blue_score == red_score:
                      winning_team = "Draw"
                     elif blue_score > red_score:
                       winning_team ="Blue"
                     else:
                      winning_team = "Red"
                     kd_ratio = player['stats']['kills'] / max(player['stats']['deaths'], 1)
                     if party_color:
                         player_info = f"- {character} {party_color} {name}  \n {kda}\n"
                     else:
                        player_info = f"- {character} {name}  \n {kda}\n"

                if player['team'] == "Blue":
                    blue_p.append((player_info, kd_ratio))
                elif player['team'] == "Red":
                    red_p.append((player_info, kd_ratio))
                else:
                    team_p.append((player_info,kd_ratio))
            blue_p.sort(key=lambda x: x[1], reverse=True) 
            red_p.sort(key=lambda x: x[1], reverse=True)
            team_p.sort(key=lambda x: x[1], reverse=True)
            
            Deathmatch_desc = "".join(info for info, _ in team_p)
            blue_team_desc = "".join(info for info, _ in blue_p)
            red_team_desc = "".join(info for info, _ in red_p)        
            if mode == "Deathmatch":
             embed.add_field(name=f"Deathmatch Players", value=Deathmatch_desc, inline=False)
            else:
             if winning_team =="Draw":
                 embed.add_field(name=f"Blue Team - {blue_score} (DRAW)", value=blue_team_desc, inline=True)
                 embed.add_field(name=f"Red Team - {red_score} (DRAW)", value=red_team_desc, inline=True)
                 
             elif winning_team == "Blue":
                 embed.add_field(name=f"Blue Team - {blue_score} (Winner)", value=blue_team_desc, inline=True)
                 embed.add_field(name=f"Red Team - {red_score}", value=red_team_desc, inline=True)
             else:
                 embed.add_field(name=f"Red Team - {red_score} (Winner)", value=red_team_desc, inline=True)
                 embed.add_field(name=f"Blue Team - {blue_score}", value=blue_team_desc, inline=True)
            

            channel = bot.get_channel(MAINCHANNEL)
            view=ChangeviewButton()
            view.add_item(discord.ui.Button(label="Tracker.gg",style=discord.ButtonStyle.link,url=f"https://tracker.gg/valorant/match/{match_id}"))
            await channel.send(embed=embed,view=view)
            
    except Exception as e:
       if latest_match['status'] == "429":
           await logger("api rate limit reached this is expected.")
       else:
           await logger(e)
       pass 





class ChangeviewButton(discord.ui.View):
    def __init__(self,*,timeout=None):
        super().__init__(timeout=None)
        

    @discord.ui.button(label="Default View",custom_id="button-1", style=discord.ButtonStyle.success)
    async def DefaultView(self, interaction: discord.Interaction, button: discord.ui.button):
     try:   
            original_message = interaction.message
            title = original_message.embeds[0].title if original_message.embeds else None
            footer = original_message.embeds[0].footer.text if original_message.embeds else None
            match_id = re.search(r"MatchID • ([\w-]+) •", footer).group(1) if footer else None
            username = re.search(r"^(.*?)'s", title).group(1) if title else None
            try:
                match = await open(f"\matches\{match_id}","r")
            except:
                match = requests.get(f"https://api.henrikdev.xyz/valorant/v2/match/{match_id}").json()

            match_data = match['data']
            match_id = match_data['metadata']['matchid']
            metadata = match_data['metadata']
            players = match_data['players']['all_players']
            map_name = metadata['map']
            game_length = convert_seconds(metadata['game_length'])
            rounds_played = metadata['rounds_played']
            mode = metadata['mode']
            date_played = metadata['game_start_patched']
            cluster = metadata['cluster']







            embed = discord.Embed(title=f"{username}'s **{mode}** Match on **{map_name}**", color=discord.Color.blue())
            embed.add_field(name="Game Length", value=game_length, inline=True)
            embed.add_field(name="Rounds Played", value=rounds_played, inline=True)
            embed.add_field(name="Server", value=cluster, inline=True)
            embed.set_footer(text=f"MatchID • {match_id} • {date_played}")
            red_score = match_data['teams']['red']['rounds_won']
            blue_score = match_data['teams']['blue']['rounds_won']
            party_id_counts = {}




            for player in players:
                party_id = player['party_id']
                if party_id in party_id_counts:
                    party_id_counts[party_id] += 1
                else:
                    party_id_counts[party_id] = 1
            color_codes = ["🔴", "🟢", "🔵", "🟡", "🟣", "🟠"]
            party_id_colors = {}

            for party_id, count in party_id_counts.items():
                if count > 1:
                    party_id_colors[party_id] = random.choice(color_codes)

            blue_p = []
            red_p = []
            team_p = []

            for player in players:
                party_id = player['party_id']
                party_color = party_id_colors.get(party_id, '')
                puuid1 = player["puuid"]
                name = player['name']
                tag = player['tag']
                character = await name2icon(player['character'].replace('/', ''))
                kda = f"{player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}"

                if mode == "Competitive":
                     if blue_score == red_score:
                      winning_team = "Draw"
                     elif blue_score > red_score:
                       winning_team ="Blue"
                     else:
                      winning_team = "Red"
                     mmrchange = await val_rr_gains(puuid1,match_id)
                     if mmrchange == None:
                        mmrchange = "0"
                     rank = player['currenttier_patched']
                     kd_ratio = player['stats']['kills'] / max(player['stats']['deaths'], 1) 
                     if party_color:
                        player_info = f"- **{mmrchange}RR** -{rank} {character} {party_color}{name} \n {kda}\n"
                     else:
                        player_info = f"- **{mmrchange}RR** -{rank} {character} {name} \n {kda}\n"
                elif mode == "Deathmatch":
                    kd_ratio = player['stats']['kills'] / max(player['stats']['deaths'], 1)
                    if party_color:
                        player_info = f"- {character} {party_color}{name} {kda}\n"
                    else:
                        player_info = f"- {character} {name} {kda}\n"
                else:
                     if blue_score == red_score:
                      winning_team = "Draw"
                     elif blue_score > red_score:
                       winning_team ="Blue"
                     else:
                      winning_team = "Red"
                     kd_ratio = player['stats']['kills'] / max(player['stats']['deaths'], 1)
                     if party_color:
                        player_info = f"- {character} {party_color}{name} {kda}\n"
                     else:
                        player_info = f"- {character} {name} {kda}\n"

                if player['team'] == "Blue":
                    blue_p.append((player_info, kd_ratio))
                elif player['team'] == "Red":
                    red_p.append((player_info, kd_ratio))
                else:
                    team_p.append((player_info,kd_ratio))
            blue_p.sort(key=lambda x: x[1], reverse=True) 
            red_p.sort(key=lambda x: x[1], reverse=True)
            team_p.sort(key=lambda x: x[1], reverse=True)
            
            Deathmatch_desc = "".join(info for info, _ in team_p)
            blue_team_desc = "".join(info for info, _ in blue_p)
            red_team_desc = "".join(info for info, _ in red_p)        
            if mode == "Deathmatch":
             embed.add_field(name=f"Deathmatch Players", value=Deathmatch_desc, inline=False)
            else:
             if winning_team =="Draw":
                 embed.add_field(name=f"Blue Team - {blue_score} (DRAW)", value=blue_team_desc, inline=True)
                 embed.add_field(name=f"Red Team - {red_score} (DRAW)", value=red_team_desc, inline=True)
                 
             elif winning_team == "Blue":
                 embed.add_field(name=f"Blue Team - {blue_score} (Winner)", value=blue_team_desc, inline=True)
                 embed.add_field(name=f"Red Team - {red_score}", value=red_team_desc, inline=True)
             else:
                 embed.add_field(name=f"Red Team - {red_score} (Winner)", value=red_team_desc, inline=True)
                 embed.add_field(name=f"Blue Team - {blue_score}", value=blue_team_desc, inline=True)
            view=ChangeviewButton()
            view.add_item(discord.ui.Button(label="Tracker.gg",style=discord.ButtonStyle.link,url=f"https://tracker.gg/valorant/match/{match_id}"))
            await interaction.response.defer()
            await interaction.message.edit(embed=embed,view=view)
            try:
             await interaction.response.defer()
            except:
                 pass
                
     except Exception as e:
       await logger(traceback.format_exc())
    @discord.ui.button(label="Text View",custom_id="button-2",style=discord.ButtonStyle.primary)
    async def textview(self, interaction: discord.Interaction, button: discord.ui.button):
        original_message = interaction.message
        title = original_message.embeds[0].title if original_message.embeds else None
        footer = original_message.embeds[0].footer.text if original_message.embeds else None
        match_id = re.search(r"MatchID • ([\w-]+) •", footer).group(1) if footer else None
        username = re.search(r"^(.*?)'s", title).group(1) if title else None
        if match_id == None:
            await interaction.response.send_message(content="error ???",view=self)
        try:
                match = await open(f"\matches\{match_id}","r")
        except:
                match = requests.get(f"https://api.henrikdev.xyz/valorant/v2/match/{match_id}").json()
        match_data = match['data']
        match_id = match_data['metadata']['matchid']
        metadata = match_data['metadata']
        players = match_data['players']['all_players']
        map_name = metadata['map']
        game_length = convert_seconds(metadata['game_length'])
        rounds_played = metadata['rounds_played']
        mode = metadata['mode']
        date_played = metadata['game_start_patched']
        cluster = metadata['cluster']
        embed = discord.Embed(title=f"{username}'s **{mode}** Match on **{map_name}**", color=discord.Color.blue())
        embed.add_field(name="Game Length", value=game_length, inline=True)
        embed.add_field(name="Rounds Played", value=rounds_played, inline=True)
        embed.add_field(name="Server", value=cluster, inline=True)
        embed.set_footer(text=f"MatchID • {match_id} • {date_played}")
        red_score = match_data['teams']['red']['rounds_won']
        blue_score = match_data['teams']['blue']['rounds_won']
        party_id_counts = {}
        for player in players:
            party_id = player['party_id']
            if party_id in party_id_counts:
                party_id_counts[party_id] += 1
            else:
                party_id_counts[party_id] = 1
        color_codes = ["🔴", "🟢", "🔵", "🟡", "🟣", "🟠"]
        party_id_colors = {}
        for party_id, count in party_id_counts.items():
            if count > 1:
                party_id_colors[party_id] = random.choice(color_codes)
        blue_p = []
        red_p = []
        team_p = []
        for player in players:
            party_id = player['party_id']
            party_color = party_id_colors.get(party_id, '')
            puuid1 = player["puuid"]
            name = player['name']
            tag = player['tag']
            level = player['level']
            character = player['character']
            score = player['stats']['score']
            kda = f"{player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}"
            if mode == "Competitive":
                 if blue_score == red_score:
                      winning_team = "Draw"
                 elif blue_score > red_score:
                   winning_team ="Blue"
                 else:
                  winning_team = "Red"
                 mmrchange = await val_rr_gains(puuid1,match_id)
                 if mmrchange == None:
                    mmrchange = "0"
                 rank = player['currenttier_patched']
                 kd_ratio = player['stats']['kills'] / max(player['stats']['deaths'], 1) 
                 if party_color:
                    player_info = f"- **{mmrchange}RR** -{party_color}{rank} {character} {name}#{tag} \n {kda}\n"
                 else:   
                    player_info = f"- **{mmrchange}RR** -{rank} {character} {name}#{tag} \n {kda}\n"
            elif mode == "Deathmatch":
                kd_ratio = player['stats']['kills'] / max(player['stats']['deaths'], 1)
                if party_color:
                    player_info = f"-{score} {party_color}{name}#{tag}[{level}] as {character} {kda}\n"
                else:
                    player_info = f"-{score} {name}#{tag}[{level}] as {character} {kda}\n"
            else:
                 if blue_score == red_score:
                    winning_team = "Draw"
                 elif blue_score > red_score:
                   winning_team ="Blue"
                 else:
                  winning_team = "Red"
                 kd_ratio = player['stats']['kills'] / max(player['stats']['deaths'], 1)
                 if party_color:
                    player_info = f"-{score} {party_color}{name}#{tag}[{level}] as {character} {kda}\n"
                 else:
                    player_info = f"-{score} {name}#{tag}[{level}] as {character} {kda}\n"
            if player['team'] == "Blue":
                blue_p.append((player_info, kd_ratio))
            elif player['team'] == "Red":
                red_p.append((player_info, kd_ratio))
            else:
                team_p.append((player_info,kd_ratio))
        blue_p.sort(key=lambda x: x[1], reverse=True) 
        red_p.sort(key=lambda x: x[1], reverse=True)
        team_p.sort(key=lambda x: x[1], reverse=True)
        
        Deathmatch_desc = "".join(info for info, _ in team_p)
        blue_team_desc = "".join(info for info, _ in blue_p)
        red_team_desc = "".join(info for info, _ in red_p)        
        if mode == "Deathmatch":
            embed.add_field(name=f"Deathmatch Players", value=Deathmatch_desc, inline=False)
        else:
             if winning_team =="Draw":
                 embed.add_field(name=f"Blue Team - {blue_score} (DRAW)", value=blue_team_desc, inline=True)
                 embed.add_field(name=f"Red Team - {red_score} (DRAW)", value=red_team_desc, inline=True)
                 
             elif winning_team == "Blue":
                 embed.add_field(name=f"Blue Team - {blue_score} (Winner)", value=blue_team_desc, inline=True)
                 embed.add_field(name=f"Red Team - {red_score}", value=red_team_desc, inline=True)
             else:
                 embed.add_field(name=f"Red Team - {red_score} (Winner)", value=red_team_desc, inline=True)
                 embed.add_field(name=f"Blue Team - {blue_score}", value=blue_team_desc, inline=True)
        view=ChangeviewButton()
        view.add_item(discord.ui.Button(label="Tracker.gg",style=discord.ButtonStyle.link,url=f"https://tracker.gg/valorant/match/{match_id}"))
                     
        await interaction.response.defer()
        await interaction.message.edit(embed=embed,view=view)
        
        


bot.run(BOTTOKEN)
