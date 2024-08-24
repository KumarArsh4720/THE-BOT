# Description: This is the main file for the bot. It contains the code for the bot to run and interact with the discord API.
import time
import os
import sys
import discord
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import config
import re
import trigger_words  # Ensure this import is correct
trigger_words = trigger_words.trigger_words




# Connect to MongoDB
mongo_connection_url = 'mongodb+srv://kumararsh4720:sP3hF7zp0Ul0QBvL@discordbot.ydzdg.mongodb.net/'
client = MongoClient(mongo_connection_url)
db = client['DISCORD_BOT']
timeouts_users_collection = db['triggered_users']

# Check if the connection is successful
try:
    # Perform a basic operation to check the connection
    users_count = timeouts_users_collection.count_documents({})
    print(f'Successfully connected to MongoDB. Triggered users collection contains {users_count} documents.')
except Exception as e:
    print(f'Failed to connect to MongoDB: {e}')

# Define the owner ID
OWNER_ID = 1090097579913650257

# Ensure the indentation is correct
try:
    # Example operation to check the configuration
    print("Configuration loaded successfully.")
except Exception as e:
    print(f"Error in configuration: {e}")

# Define a custom check to ensure the command is run by the owner of the bot

def is_owner():
    def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return commands.check(predicate)




# Define the bot's command prefix
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)






logging_channels = {
    1233154030461648936: 1273701238843637902,  # Replace with actual server and logging channel IDs
    1267447773347840020: 1267866588695101491,  # Add more server and logging channel ID pairs as needed
}

# Dictionaries to store error channel IDs and role IDs for each server
error_channels = {
    1233154030461648936: 1273701238843637902,
    1267447773347840020: 1267866588695101491,  # Example: {server_id: error_channel_id}
    # Add more server_id: error_channel_id pairs as needed
}

role_ids = {
    1233154030461648936: 1233154030461648939,  # Example: {server_id: role_id}
    # Add more server_id: role_id pairs as needed
}

# This is the main cog for the bot. It contains the code for the bot to run and interact with the discord API.

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="with servers"))
    await bot.tree.sync()
    print(f'Logged in as {bot.user.name}')
    cleanup_timeouts.start()  # Start the background task

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    print(f'Received message: {message.content}')

    # Check for whole word trigger
    if any(re.search(rf'\b{re.escape(word)}\b', message.content.lower()) for word in trigger_words):
        print(f'Trigger word detected in message: {message.content}')  # Debug: Trigger word detected
        duration = 60  # Timeout duration in seconds
        current_time = int(time.time())

        try:
            # Update the timeout information and trigger count in the database
            timeout_end = current_time + duration
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            result = timeouts_users_collection.find_one_and_update(
                {'user_id': message.author.id},
                {
                    '$set': {'timeout_end': timeout_end, 'last_triggered': datetime.now(timezone.utc)},
                    '$inc': {'trigger_count': 1}
                },
                upsert=True,
                return_document=True
            )
            print(f'Successfully updated MongoDB.')
        except Exception as e:
            print(f'Error updating MongoDB: {e}')
            return

        try:
            # Get the member object
            member = message.guild.get_member(message.author.id)
            if member:
                # Apply the timeout to the member
                await member.timeout(timedelta(seconds=timeout_end - current_time))
        except Exception as e:
            print(f'Error applying timeout: {e}')
            return

        try:
            # Check if the user should be banned
            if result and result['trigger_count'] >= 5:
                # Ban the user if they have triggered more than 5 times in the last hour
                await member.ban(reason="Triggered banned words more than 5 times in an hour")
                print(f'User {message.author.id} banned for exceeding trigger limit')
        except Exception as e:
            print(f'Error updating trigger count or banning user: {e}')
            return

        try:
            await message.channel.send(f'{message.author.mention}, you have been timed out for {timeout_end - current_time} seconds.')
            print(f'{message.author.name} has been timed out for {timeout_end - current_time} seconds.')
        except Exception as e:
            print(f'Error sending timeout notification: {e}')
        return
    else:
        print('No trigger word detected in message.')  # Debug: No trigger word detected

    # Process other bot commands if any
    try:
        await bot.process_commands(message)
    except Exception as e:
        print(f'Error processing commands: {e}')

@tasks.loop(minutes=10)  # Run every 10 minutes
async def cleanup_timeouts():
    try:
        # Calculate the threshold time (e.g., 1 hour ago)
        threshold_time = int(time.time()) - 3600  # 3600 seconds = 1 hour
        result = timeouts_users_collection.delete_many({'timeout_end': {'$lt': threshold_time}})
        print(f'Cleanup result: {result.deleted_count} documents deleted.')
    except Exception as e:
        print(f'Error during cleanup: {e}')

# Define the on_slash_command_error event handler
@bot.event
async def on_slash_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send('You do not have the required permissions to run this command.', ephemeral=True)
    elif isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the required permissions to run this command.', ephemeral=True)
    elif isinstance(error, commands.errors.CommandOnCooldown):
        await ctx.send(f'This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.', ephemeral=True)
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send('Command not found.', ephemeral=True)
    else:
        await ctx.send('An error occurred while processing the command.', ephemeral=True)
        print(f'Error: {error}')


    
#MODERATION COMMANDS


@bot.event
async def on_guild_role_create(role: discord.Role):
    try:
        role_id = 1267869458500681759
        alert_channel_id = 1267866588695101491
        alert_channel = bot.get_channel(alert_channel_id)
        role = role.guild.get_role(role_id)
        if alert_channel:
            # Make the role temporarily mentionable
            await role.edit(mentionable=True)
            # Send the alert message
            await alert_channel.send(f'{role.mention}⚠️ALERT⚠️, {role.mention} has been created in the server! Please check it out! 🚨')
            # Set the role back to not mentionable
            await role.edit(mentionable=False)
    except Exception as e:
        print(f"Error sending role creation alert: {e}")



@bot.event
async def on_guild_role_delete(role: discord.Role):
    role_id = 1267869458500681759
    alert_channel_id = 1267866588695101491
    alert_channel = bot.get_channel(alert_channel_id)
    role = channel.guild.get_role(role_id)
    if alert_channel:
        await alert_channel.send(f'{role.mention}⚠️ALERT⚠️, {role.name} has been deleted in the server! Please check it out! 🚨')



@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    role_id = 1267869458500681759
    alert_channel_id = 1267866588695101491  
    alert_channel = bot.get_channel(alert_channel_id)
    role = channel.guild.get_role(role_id)
    if alert_channel:
        await alert_channel.send(f'{role.mention}⚠️ALERT⚠️, {channel.mention} has been created in the server! Please check it out! 🚨')
     

@bot.event
async def on_guild_channel_delete(channel):
    role_id = 1267869458500681759
    alert_channel_id = 1267866588695101491
    alert_channel = bot.get_channel(alert_channel_id)
    role = channel.guild.get_role(role_id)
    if alert_channel:
        await alert_channel.send(f'{role.mention}The channel "{channel.name}" was deleted.')




@bot.event
async def on_member_join(member):
    welcome_settings = {
        'GAMERS_TOWN': {
            'title': '💐 WELCOME_ALERT 💐',
            'message': 'Welcome to {guild.name}, {member.mention}!',
            'banner_url': 'https://i.pinimg.com/originals/b3/4b/d0/b34bd0ef85660338e6082332e0d31a7f.gif',  # Replace with the actual URL of the banner image
            'channel_id': 1233154030461648945  # Replace with the actual channel ID for GAMERS_TOWN
        },
        'KING THE RULER SUPPORT': {
            'title': 'Welcome to King The Ruler Support!',
            'message': 'Welcome to {guild.name}, {member.mention}!',
            'banner_url': 'https://i.pinimg.com/originals/b3/4b/d0/b34bd0ef85660338e6082332e0d31a7f.gif',  # Replace with the actual URL of the banner image
            'channel_id': 1267866416816853022  # Replace with the actual channel ID for KING THE RULER SUPPORT
        },
        # Add more servers and their welcome settings here
    }

    guild_name = member.guild.name
    settings = welcome_settings.get(guild_name, {
        'title': 'Welcome!',
        'message': f'Welcome to {guild_name}, {member.mention}!',
        'banner_url': None,
        'channel_id': None  # Default to None if no specific channel is set
    })
    
    welcome_title = settings['title']
    welcome_message = settings['message'].format(guild=member.guild, member=member)
    banner_url = settings['banner_url']
    channel_id = settings['channel_id']
    
    print(f'New member joined: {member.name} in guild: {guild_name}')  # Debug print
    print(f'Welcome message: {welcome_message}')  # Debug print
    print(f'Channel ID: {channel_id}')  # Debug print
    
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel is None:
            print(f'Channel with ID {channel_id} not found in cache. Fetching from API...')
            channel = await bot.fetch_channel(channel_id)
    else:
        # Fallback to a default channel if no specific channel is set
        channel = discord.utils.get(member.guild.text_channels, name='general')
    
    if channel:
        embed = discord.Embed(title=welcome_title, description=welcome_message, color=0x00ff00)
        if banner_url:
            embed.set_image(url=banner_url)
        await channel.send(embed=embed)
        print(f'Sent welcome message to {channel.name}')  # Debug print
    else:
        print('No valid channel found to send the welcome message')  # Debug print

   














#OWNER COMMANDS
@bot.tree.command()
@commands.is_owner()  # This ensures only the owner of the bot can run this command
async def shutdown(interaction:discord.Interaction):
    await interaction.response.send_message('Shutting down...')
    await bot.close()


#PUBLIC COMMANDS 

@bot.tree.command()
async def ping(interaction:discord.Interaction):
    await interaction.response.send_message('Pong!')


@bot.tree.command()
async def info(interaction: discord.Interaction):
   
    user = interaction.user  # Get the user who invoked the command
    guild = interaction.guild  # Get the guild where the command was invoked
    guild_icon = interaction.guild.icon.url

    embed = discord.Embed(
        title='**SERVER INFO**', 
        description='Here is the all details about the server!', 
        color=0xf20c1f
        )
    
    embed.set_thumbnail(
        url=guild_icon
    )
    embed.set_footer(
        text='This is the Footer',
        icon_url="https://media.discordapp.net/attachments/1261363178206396489/1267522692542763068/discord-icon-2048x2048-o5mluhz2.png?ex=66a917ff&is=66a7c67f&hm=816479600f27215e765c06f2af32a8b713a60d3e1e4dc56aeb3823c72cace2ad&=&format=webp&quality=lossless&width=437&height=437"
    )
    

    embed.add_field(name='Name:', value=guild.name, inline=False)
    embed.add_field(name='Owner:', value=guild.owner.mention, inline=False)
    embed.add_field(name='Members:', value=guild.member_count, inline=True)
    embed.add_field(name='Created at:', value=guild.created_at.strftime("||%A, %B %d, %Y %I:%M %p||"), inline=False)
    embed.add_field(name='Server boost:', value=f" Level {guild.premium_tier}", inline=False)
    embed.add_field(name='Verification Level:', value=guild.verification_level, inline=True)
    await interaction.response.send_message(embed=embed)

    

@bot.tree.command()
@is_owner()
async def token(ctx):
    try:
        await ctx.send('HELLO', ephemeral=True)
    except commands.errors.NotOwner:
        print("The command was attempted by a non-owner.")
    except Exception as e:
        print(f"Error: {e}")









@bot.tree.command(name='timeout')
@app_commands.checks.has_permissions(administrator=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, duration: int):
    """Timeout a user for a specified duration in seconds."""
    timeout_end = int(time.time()) + duration
    print(f'Setting timeout end for {member.name} to: {timeout_end}')

    try:
        await interaction.response.send_message(f'{member.mention} has been timed out for {duration} seconds.')
        print(f'{member.name} has been timed out for {duration} seconds.')
    except Exception as e:
        print(f'Error sending timeout notification: {e}')





@bot.command(name='refresh')
@commands.has_permissions(administrator=True)
async def refresh(ctx):
    """Refreshes the bot by restarting it."""
    await ctx.send('Refreshing the bot...')
    print('Refreshing the bot...')

    # Stop the bot
    await bot.close()

    # Restart the bot
    os.execv(sys.executable, ['python'] + sys.argv)





bot.run(config.TOKEN)