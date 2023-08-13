import os
import requests
from PIL import Image
from io import BytesIO
import discord
import json
from discord.ext import commands
import asyncio
os.makedirs("assets", exist_ok=True)
TOKEN= "DISCORD BOT TOKEN HERE"
server_id = 'SERVER ID HERE'# i advice making a new discord server and adding the bot to it to store the emojis there, make sure the bot has admin permissions and all intents enabled in developer portal. (No the bot does not have to be used in that new server it just needs to be present inside it, to use the emojis.)


intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')


@bot.command()
async def download(ctx):
    await ctx.reply("Downloading please wait...")
    base_url = "https://valorant-api.com/v1/agents"
    response = requests.get(base_url)
    agents_data = response.json()["data"]

    for agent in agents_data:
        name = agent["displayName"]
        name_safe = name.replace("/", "") 
        icon_url = agent["displayIcon"]

        response = requests.get(icon_url)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))

            image_path = os.path.join("assets", f"{name_safe}.png")
            image.save(image_path)
            print(f"Downloaded {name}'s icon.")
    print("Emojis have been downloaded")
    await ctx.reply("Emojis have been downloaded, run !upload (make sure i admin!)")

@bot.command()
async def upload(ctx):
    ctx.reply("Uploading please wait")
    assets_folder = "assets"
    emoji_list = {}
    uploaded_emojis = set()

    if os.path.exists("emoji_list.json"):
        with open("emoji_list.json", "r") as f:
            emoji_list = json.load(f)
            uploaded_emojis = set(emoji_list.keys())

    for filename in os.listdir(assets_folder):
        if filename.endswith('.png'):
            emoji_name = os.path.splitext(filename)[0]

            if emoji_name in uploaded_emojis:
                print(f"Skipping {emoji_name}, already uploaded.")
                continue

            image_path = os.path.join(assets_folder, filename)

            with open(image_path, 'rb') as f:
                emoji_bytes = f.read()

            try:
                emoji = await ctx.guild.create_custom_emoji(name=emoji_name, image=emoji_bytes)
                emoji_list[emoji.name] = str(emoji.id)
            except discord.Forbidden:
                print(f"Could not upload emoji: {emoji_name} - Insufficient permissions")
            except discord.HTTPException:
                print(f"Could not upload emoji: {emoji_name} - HTTP error occurred")

    with open("emoji_list.json", "w") as f:
        json.dump(emoji_list, f, indent=4)

    print("Emoji upload process completed. Emoji names and IDs saved in emoji_list.json")
    await ctx.reply("Emoji upload process completed. Emoji names and IDs saved in emoji_list.json")
bot.run(TOKEN)