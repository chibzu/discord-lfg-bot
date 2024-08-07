import discord


bot_token = ""

with open("./discord.token") as f:
    bot_token = f.read()
    

class ChibbleBot(discord.Client):
    async def on_ready(self):
            print(f'Logged on as {self.user}!')
            
    async def on_message(self, message):
            print(f'Message from {message.author}: {message.content}')
            
intents = discord.Intents.default()
intents.message_content = True

chibblebot = ChibbleBot(intents=intents)
chibblebot.run(bot_token)
