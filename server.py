import discord
import textwrap
import pickle
import asyncio

bot_token = ""
with open("./discord.token") as f:
    bot_token = f.read()
    
# {[userID] => {message, emoji, guild}}
pending_associations = {}
# {[guildID] => [{emoji, game}]}
guild_game_associations = {}

# 
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
    async def load_from_disk(self):
        try:
            with open("./data/pending_associations.dat", "rb") as file:
                global pending_associations
                pending_associations = pickle.load(file)   
            # print("Loaded pending_associations")
            # print(pending_associations)
        
            with open("./data/guild_game_associations.dat", "rb") as file:
                global guild_game_associations
                guild_game_associations = pickle.load(file)
            # print("Loaded guild_game_associations")
            # print(guild_game_associations)   
            
             
            with open("./data/guild_user_schedules.dat", "rb") as file:
                global guild_user_schedules
                guild_user_schedules = pickle.load(file)
            # print("Loaded guild_user_schedules")
            # print(guild_user_schedules)
                
            with open("./data/guild_messages.dat", "rb") as file:
                global guild_messages
                simple_guild_messages = pickle.load(file)
                
                for guild, messages in simple_guild_messages.items():
                    channel = await self.fetch_channel(messages["channel"])
                    guild_messages[guild] = {}
                    guild_messages[guild]["channel"] = channel.id
                    guild_messages[guild]["game_interests"] = await channel.fetch_message(messages["game_interests"])
                    guild_messages[guild]["weekly_schedule"] = await channel.fetch_message(messages["weekly_schedule"])
                    guild_messages[guild]["schedule_suggestion"] = await channel.fetch_message(messages["schedule_suggestion"])
            # print("Loaded guild_messages")
            # print(guild_messages)
                
        except Exception as e:
            print("Error Loading From Disk")
            print(e)
    
    def save_to_disk(self):
        try:
            with open("./data/pending_associations.dat", "wb") as file:
                pickle.dump(pending_associations, file, pickle.HIGHEST_PROTOCOL)
            # print("Saved pending_associations")
            # print(pending_associations)
        except Exception as e:
            print("Error Saving pending_associations To Disk")
            print(e)
            
        try:
            with open("./data/guild_game_associations.dat", "wb") as file:
                pickle.dump(guild_game_associations, file, pickle.HIGHEST_PROTOCOL)
            # print("Saved guild_game_associations")
            # print(guild_game_associations)                
        except Exception as e:
            print("Error Saving guild_game_associations To Disk")
            print(e)
                
        try:
            with open("./data/guild_user_schedules.dat", "wb") as file:
                pickle.dump(guild_user_schedules, file, pickle.HIGHEST_PROTOCOL)
            # print("Saved guild_user_schedules")
            # print(guild_user_schedules)                
        except Exception as e:
            print("Error Saving guild_user_schedules To Disk")
            print(e)
            
        try:                
            with open("./data/guild_messages.dat", "wb") as file:
                try:
                    simple_guild_messages = {}
                    for guild, messages in guild_messages.items():
                        simple_guild_messages[guild] = { 
                                                            "channel": messages["channel"], 
                                                            "game_interests": messages["game_interests"].id, 
                                                            "weekly_schedule": messages["weekly_schedule"].id, 
                                                            "schedule_suggestion": messages["schedule_suggestion"].id
                                                    }
                except Exception as e:
                    print("Failed to serialize guild_messages")
                    print(e)
                pickle.dump(simple_guild_messages, file, pickle.HIGHEST_PROTOCOL)
            # print("Saved simple_guild_messages")
            # print(simple_guild_messages)
            
        except Exception as e:
            print("Error Saving guild_messages To Disk")
            print(e.__class__.__name__)
                    
    
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
                emoji_name = self.get_normalized_reaction_name(reaction)                
                return emoji_name == payload.emoji.name
            reaction = next(filter(findReaction, reacted_message.reactions))
            emoji_name = self.get_normalized_reaction_name(reaction)   
            
            if reaction.count == 1:
                reacting_user = await self.fetch_user(payload.user_id)
                pending_associations[reacting_user.id] = { "emoji": emoji_name, "guild": payload.guild_id }
                await reacting_user.send(f"Looks like you added a new reaction emoji, what game should {emoji_name} represent?")
            else: 
                user_schedules = guild_user_schedules[payload.guild_id]
                if payload.user_id not in user_schedules:
                    user_schedules[payload.user_id] = { "games": [], "days": []}
                    
                game_associations = guild_game_associations[payload.guild_id]
                def findAssociation(assoc):
                    return assoc["emoji"] == emoji_name
                association = next(filter(findAssociation, game_associations))            
                user_schedules[payload.user_id]["games"].append(association["game"])            
              
        if reacted_message.id == guild_messages[payload.guild_id]["weekly_schedule"].id:
            user_schedules = guild_user_schedules[payload.guild_id]
            if payload.user_id not in user_schedules:
                user_schedules[payload.user_id] = { "games": [], "days": []}
                
            game_associations = guild_game_associations[payload.guild_id]      
            user_schedules[payload.user_id]["days"].append(week_emoji_map[payload.emoji.name])
            
                   
     
        await self.update_schedule_suggestion(payload.guild_id)
        self.save_to_disk()          
                
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        reaction_channel = await self.fetch_channel(payload.channel_id)        
        reacted_message = await reaction_channel.fetch_message(payload.message_id)   
                
        # If message being reacted to isn't the bot's do nothing
        if reacted_message.author.id != self.user.id:
            return
        # If reaction is made by the bot, do nothing
        if payload.user_id == self.user.id:
            return
        
        if reacted_message.id == guild_messages[payload.guild_id]["game_interests"].id:
            def findReaction(reaction):
                emoji_name = self.get_normalized_reaction_name(reaction)     
                return emoji_name == payload.emoji.name
            reaction = next(filter(findReaction, reacted_message.reactions), None)
            
            if (reaction == None):
                game_associations = guild_game_associations[payload.guild_id]
                def findAssociation(assoc):
                    return assoc["emoji"] == self.get_normalized_reaction_name(payload)
                association = next(filter(findAssociation, game_associations))
                game_associations.remove(association)
                
                game_interests_str = "# What'cha Playing This Week?\n\n"
                if len(guild_game_associations[payload.guild_id]) == 0:
                    game_interests_str += "No games being played yet, add an emoji reaction to this message to get started!"
                else:
                    for game_association in guild_game_associations[payload.guild_id]:
                        game_interests_str += f"{game_association["emoji"]} - {game_association["game"]}\n"
                
                game_interests_str += "-# Add new reactions to add games\n\n\n"
                interests_to_update = guild_messages[payload.guild_id]["game_interests"]
                await interests_to_update.edit(content=game_interests_str)
            
            user_schedules = guild_user_schedules[payload.guild_id]      
            user_schedules[payload.user_id]["games"].remove(association["game"])
            
            await self.update_schedule_suggestion(payload.guild_id)
            
        if reacted_message.id == guild_messages[payload.guild_id]["weekly_schedule"].id:
            user_schedules = guild_user_schedules[payload.guild_id]
            if payload.user_id not in user_schedules:
                return
                
            game_associations = guild_game_associations[payload.guild_id]
            user_schedules[payload.user_id]["days"].remove(week_emoji_map[payload.emoji.name])
            
            await self.update_schedule_suggestion(payload.guild_id)
            
        self.save_to_disk()    
        
        
            
    # async def on_raw_reaction_clear_emoji(self, payload: discord.RawReactionActionEvent):
    #     print("on_raw_reaction_clear_emoji")    
    #     # If message being reacted to isn't the bot's do nothing
    #     if payload.message_author_id != self.user.id:
    #         return
    #     # If reaction is made by the bot, do nothing
    #     if payload.user_id == self.user.id:
    #         return
        
    #     reaction_channel = await self.fetch_channel(payload.channel_id)        
    #     reacted_message = await reaction_channel.fetch_message(payload.message_id)
        
    #     if reacted_message.id == guild_messages[payload.guild_id]["game_interests"].id:        
    #         def findReaction(reaction):
    #             return reaction.emoji == payload.emoji.name
    #         reaction = next(filter(findReaction, reacted_message.reactions))
            
    #         user_schedules = guild_user_schedules[payload.guild_id]
    #         game_associations = guild_game_associations[payload.guild_id]
    #         def findAssociation(assoc):
    #             return assoc["emoji"] == reaction.emoji
    #         association = next(filter(findAssociation, game_associations))
    #         game_associations.remove(association)     
                   
    #         user_schedules[payload.user_id]["games"].remove(association["game"])
            
    #         await self.update_schedule_suggestion(payload.guild_id)
            
    #     self.save_to_disk()
        
     
    async def on_message(self, message: discord.Message):
        # Don't respond to the bot's own messages        
        if message.author.id == self.user.id:
            return
        # Only respond to DMs
        if message.guild != None:
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
            del pending_associations[message.author.id]
            await message.author.send(f"Got it! {game_association["emoji"]} means {game_association["game"]}")
            
            user_schedules = guild_user_schedules[pending_association["guild"]]
            if message.author.id not in user_schedules:
                user_schedules[message.author.id] = { "games": [], "days": []}
                
            game_associations = guild_game_associations[pending_association["guild"]]
            def findAssociation(assoc):
                return assoc["emoji"] == game_association["emoji"]
            association = next(filter(findAssociation, game_associations))            
            user_schedules[message.author.id]["games"].append(association["game"])
            
            await self.update_schedule_suggestion(pending_association["guild"])
            self.save_to_disk()
    
    async def on_ready(self):
            print(f"Logged on as {self.user}!")
            
            await self.load_from_disk()
            
            guilds = chibblebot.fetch_guilds()
            async for guild in guilds:
                
                if (guild.id in guild_messages):
                    continue
                
                guild_game_associations[guild.id] = []
                guild_user_schedules[guild.id] = {}
                    
                channels = await guild.fetch_channels()
                for channel in channels:
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
                        
                        
                        guild_messages[guild.id] = {"channel": channel.id, "game_interests": game_interests, "weekly_schedule": weekly_schedule, "schedule_suggestion": schedule_suggestion}
                        guild_game_associations[guild.id] = []
                        
                        self.save_to_disk()
                        
    async def update_schedule_suggestion(self, guild_id):   
        quorum_threshold = 2                              
        # Update the possibility calendar message
        week_analysis = [[], [], [], [], [], [], []]
        user_schedules = guild_user_schedules[guild_id]
        print("update_schedule_suggestion")
        print(user_schedules)
        for schedule in user_schedules.values():
            for day in schedule["days"]:
                for game in schedule["games"]:
                    week_analysis[day].append(game)

        week_analysis_str = ""
        game_associations = guild_game_associations[guild_id]
        print(game_associations)
        at_least_one_quorum = False
        for day in range(len(week_analysis)):
            quorum = False
            day_str = ""            
            for association in game_associations:
                if week_analysis[day].count(association["game"]) > quorum_threshold:
                    day_str += f"{association["game"]}, "
                    quorum = True
                    at_least_one_quorum = True
            if quorum:
                week_analysis_str += f"**{day_name_map[day]}**: {day_str[:-2]} \n"
                
        schedule_suggestion = guild_messages[guild_id]["schedule_suggestion"]                
        if at_least_one_quorum:            
            new_schedule = "# Possibly Good Days To Game\n\n"
            new_schedule += week_analysis_str
            new_schedule += "\n"
                
            await schedule_suggestion.edit(content=new_schedule)
        else:
            await schedule_suggestion.edit(content=textwrap.dedent(""" 
                # Possibly Good Days To Game
                
                No Days Currently Lining Up  :|                                                      
            """))
            
    def get_normalized_reaction_name(self, reaction):
        if (isinstance(reaction.emoji, discord.PartialEmoji)):
            return reaction.emoji.name
        else:
            return reaction.emoji
            
         
         
intents = discord.Intents.default()
intents.message_content = True

chibblebot = ChibbleBot(intents=intents)

chibblebot.run(bot_token)
