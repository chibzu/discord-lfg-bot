import discord
import textwrap
from pprint import pprint

bot_token = ""
with open("./discord.token") as f:
    bot_token = f.read()
    
    
pending_associations = {}
guild_game_associations = {}
guild_user_schedules = {}
guild_messages = {}

week_emoji_map = {
    "1️⃣": 0,
    "2️⃣": 1,
    "3️⃣": 2,
    "4️⃣": 3,
    "5️⃣": 4,
    "6️⃣": 5,
    "7️⃣": 6
}

day_name_map = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

class ChibbleBot(discord.Client):
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # If message being reacted to isn't the bot's do nothing
        if payload.message_author_id != self.user.id:
            return
        # If reaction is made by the bot, do nothing
        if payload.user_id == self.user.id:
            return
        
        reaction_channel = await self.fetch_channel(payload.channel_id)        
        reacted_message = await reaction_channel.fetch_message(payload.message_id)
        
        if reacted_message.id == guild_messages[payload.guild_id]["game_interests"].id:        
            def findReaction(reaction):
                return reaction.emoji == payload.emoji.name
            reaction = next(filter(findReaction, reacted_message.reactions))
            
            if reaction.count == 1:
                reacting_user = await self.fetch_user(payload.user_id)
                pending_associations[reacting_user.id] = { "message": reacted_message, "emoji": reaction.emoji, "guild": payload.guild_id }
                await reacting_user.send(f"Looks like you added a new reaction emoji, what game should {reaction.emoji} represent?")
            else: 
                user_schedules = guild_user_schedules[payload.guild_id]
                if payload.user_id not in user_schedules:
                    user_schedules[payload.user_id] = { "games": [], "days": []}
                    
                game_associations = guild_game_associations[payload.guild_id]
                def findAssociation(assoc):
                    return assoc["emoji"] == reaction.emoji
                association = next(filter(findAssociation, game_associations))            
                user_schedules[payload.user_id]["games"].append(association["game"])
                
                print(user_schedules)
                
        if reacted_message.id == guild_messages[payload.guild_id]["weekly_schedule"].id:
            user_schedules = guild_user_schedules[payload.guild_id]
            if payload.user_id not in user_schedules:
                user_schedules[payload.user_id] = { "games": [], "days": []}
                
            game_associations = guild_game_associations[payload.guild_id]      
            user_schedules[payload.user_id]["days"].append(week_emoji_map[payload.emoji.name])
            
            print(user_schedules)
                   
     
        await self.update_schedule_suggestion(payload.guild_id)
                
     
    async def on_message(self, message: discord.Message):
        # Don't respond to the bot's own messages        
        if message.author.id == self.user.id:
            return
        
        if message.author.id in pending_associations:
            pending_association = pending_associations[message.author.id]
            guild_game_associations[pending_association["guild"]].append({ "emoji": pending_association["emoji"], "game": message.content})
            
            game_interests_str = "# What'cha Playing This Week?\n\n"
            if len(guild_game_associations[pending_association["guild"]]) == 0:
                game_interests_str += "No games being played yet, add an emoji reaction to this message to get started!"
            else:
                for game_association in guild_game_associations[pending_association["guild"]]:
                    game_interests_str += f"{game_association["emoji"]} - {game_association["game"]}\n"
            
            game_interests_str += "-# Add new reactions to add games\n\n\n"
            interests_to_update = guild_messages[pending_association["guild"]]["game_interests"]
            await interests_to_update.edit(content=game_interests_str)
            pending_associations[message.author.id] = None
            await message.author.send(f"Got it! {game_association["emoji"]} means {game_association["game"]}")
            
            user_schedules = guild_user_schedules[pending_association["guild"]]
            if message.author.id not in user_schedules:
                user_schedules[message.author.id] = { "games": [], "days": []}
                
            game_associations = guild_game_associations[pending_association["guild"]]
            def findAssociation(assoc):
                return assoc["emoji"] == game_association["emoji"]
            association = next(filter(findAssociation, game_associations))            
            user_schedules[message.author.id]["games"].append(association["game"])
            
            print(user_schedules)
            await self.update_schedule_suggestion(pending_association["guild"])
    
    async def on_ready(self):
            print(f"Logged on as {self.user}!")
            guilds = chibblebot.fetch_guilds()
            async for guild in guilds:
                
                
                guild_game_associations[guild.id] = []
                guild_user_schedules[guild.id] = {}
                guild_file = None
                try:
                   guild_file = open(f"./{guild.id}", "r")
                   guild_file.close()
                except Exception as e:
                    guild_file = open(f"./{guild.id}", "w")
                    # Init per server metadata here            
                    guild_file.write("")
                    guild_file.close()
                    
                    
                channels = await guild.fetch_channels()
                for channel in channels:
                    print(channel, channel.type)
                    if (channel.type == discord.ChannelType.text and channel.name == "lfg-chibblebot"):
                        await channel.send(".\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n.") 
                        
                        
                        game_interests_str = "# What'cha Playing This Week?\n\n"
                        if len(guild_game_associations[guild.id]) == 0:
                            game_interests_str += "No games being played yet, add an emoji reaction to this message to get started!\n\n\n"
                        else:
                            for game_association in guild_game_associations[guild.id]:
                                game_interests_str += f"{game_association.emoji} - {game_association.game}\n"
                                game_interests_str += "-# Add new reactions to add games\n\n\n"                                
                                                    
                        game_interests = await channel.send(textwrap.dedent(game_interests_str))                                        
                        
                        weekly_schedule = await channel.send(textwrap.dedent("""
                            # Weekly LFG Schedule

                            React to this message to indicate which days of the week you'll probably be looking for games:
                            1️⃣ Monday - 2️⃣ Tuesday - 3️⃣ Wednesday
                            4️⃣ Thursday - 5️⃣ Friday - 6️⃣ Saturday - 7️⃣ Sunday
                        """)) 
                        
                        await weekly_schedule.add_reaction("1️⃣")
                        await weekly_schedule.add_reaction("2️⃣")
                        await weekly_schedule.add_reaction("3️⃣")
                        await weekly_schedule.add_reaction("4️⃣")
                        await weekly_schedule.add_reaction("5️⃣")
                        await weekly_schedule.add_reaction("6️⃣")
                        await weekly_schedule.add_reaction("7️⃣")
                        
                        schedule_suggestion = await channel.send(textwrap.dedent(""" 
                            # Possibly Good Days To Game
                            
                            No Days Currently Lining Up  :|                                                      
                        """))
                        
                        
                        guild_messages[guild.id] = {"game_interests": game_interests, "weekly_schedule": weekly_schedule, "schedule_suggestion": schedule_suggestion}
                        guild_game_associations[guild.id] = []
                        
    async def update_schedule_suggestion(self, guild_id):                                 
        # Update the possibility calendar message
        week_analysis = [[], [], [], [], [], [], []]
        user_schedules = guild_user_schedules[guild_id]
        for schedule in user_schedules.values():
            for day in schedule["days"]:
                for game in schedule["games"]:
                    week_analysis[day].append(game)

        print(week_analysis)
        week_analysis_str = ""
        game_associations = guild_game_associations[guild_id]
        at_least_one_quorum = False
        for day in range(len(week_analysis)):
            quorum = False
            day_str = ""            
            for association in game_associations:
                if week_analysis[day].count(association["game"]) > 1:
                    day_str += f"{association["game"]}, "
                    quorum = True
                    at_least_one_quorum = True
            if quorum:
                week_analysis_str += f"**{day_name_map[day]}**: {day_str[:-2]} \n"
                
        if at_least_one_quorum:
            schedule_suggestion = guild_messages[guild_id]["schedule_suggestion"]
            new_schedule = "# Possibly Good Days To Game\n\n"
            new_schedule += week_analysis_str
            new_schedule += "\n"
                
            await schedule_suggestion.edit(content=new_schedule)
            
            
intents = discord.Intents.default()
intents.message_content = True

chibblebot = ChibbleBot(intents=intents)
chibblebot.run(bot_token)

