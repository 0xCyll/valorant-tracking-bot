
# Valorant Tracking Bot

**Valorant Tracking Bot** is a simple way to track player's matches on Discord! 🎮

## Setup

### Python Environment

1. Open your desired terminal.
2. Run the following command to install the required Python packages:
   ```
   pip3 install -r requirements.txt
   ```

### Tracking Users

1. Configure the bot by entering the required data inside the bot's configuration file.
2. The data for tracking users' matches is stored in `tracked_users.json`.
3. You can start by adding a single user's data, and then later add more users using commands.

### Setting Up Emojis for Character Icons

1. Fill out the `setup.py` file, providing your server's ID and your Discord bot token.
2. To ensure proper functionality, it's recommended to create a new Discord server.
3. Invite the bot to your server and grant it admin permissions and all the intents in the Discord Developer Portal.
   (Note: While the bot doesn't need to be actively running on the server, it does need to be a member to use the emojis.)

## Usage

1. Once the setup is complete, the bot will automatically track the specified users' matches.
2. You can use Slash commands to manage and add additional users to be tracked.

## Contributing

Feel free to contribute by submitting issues or pull requests to improve the bot!

---

By using the **Valorant Tracking Bot**, you can keep tabs on your favorite players' matches directly on Discord. Enjoy tracking the action! 🎉