import sys

import discord
from discord.ext import commands
from discord import app_commands, Permissions
import random

from files.log import setup_logging, handle_exception

class GameCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
        self.logger = setup_logging()
        sys.excepthook = handle_exception

        self.fishing_channel:discord.TextChannel|None = None
        self.end_word_channel:discord.TextChannel|None = None
        self.menu_channel:discord.TextChannel|None = None
        self.menus = []
        self.fish_list = ["물고기"]
        self.last_word = None

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if message.author.bot:
            return

        # 끝말잇기 채널에서의 메시지 처리
        if self.end_word_channel and message.channel.id == self.end_word_channel.id:
            await self.handle_end_word(message)

        # 낚시 채널에서의 메시지 처리
        elif self.fishing_channel and message.channel.id == self.fishing_channel.id:
            if message.content.lower() == "낚시":
                view = FishingView(self.fish_list)
                await message.channel.send("🎣 낚시찌를 던졌다! (첨벙)", view=view, delete_after=30)

        # 메뉴 추천 채널에서의 메시지 처리
        elif self.menu_channel and message.channel.id == self.menu_channel.id:
            await self.handle_menu_recommendation(message)

    async def handle_end_word(self, message:discord.Message):
        if message.content == "끝말잇기 시작":
            self.last_word = None
            await message.channel.send("끝말잇기를 시작합니다! 첫 단어를 입력하세요.")
        elif message.content == "끝말잇기 끝":
            self.last_word = None
            await message.channel.send("끝말잇기를 종료합니다.")
        elif self.last_word is None:
            self.last_word = message.content
            await message.channel.send(f"끝말잇기 시작! 첫 단어는 '{message.content}' 입니다.")
        else:
            if message.content.startswith(self.last_word[-1]):
                self.last_word = message.content
                await message.channel.send(f"'{message.content}' 추가 완료! 다음 단어를 입력하세요.")
            else:
                await message.channel.send(f"'{message.content}'는(은) '{self.last_word[-1]}'로 시작하지 않습니다. 다시 시도해 주세요.")
    
    async def handle_menu_recommendation(self, message:discord.Message):
        if message.content == "메뉴추천":
            menu = random.choice(self.menus)
            await message.channel.send(f"오늘의 추천 메뉴는 '{menu}'입니다!")

    @app_commands.command(name="끝말잇기채널설정")
    async def 끝말잇기채널설정(self, interaction:discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        self.end_word_channel = channel
        await interaction.followup.send(content=f"끝말잇기 채널이 설정되었습니다: {channel.mention}", ephemeral=True)

    @app_commands.command(name="낚시채널설정")
    async def 낚시채널설정(self, interaction:discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        self.fishing_channel = channel
        await interaction.followup.send(content=f"낚시 채널이 설정되었습니다: {channel.mention}", ephemeral=True)

    @app_commands.command(name="메뉴추천채널설정")
    async def 메뉴추천채널설정(self, interaction:discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        self.menu_channel = channel
        await interaction.followup.send(content=f"메뉴추천 채널이 설정되었습니다: {channel.mention}", ephemeral=True)

    @app_commands.command(name="메뉴추가", description="추천 메뉴에 새로운 메뉴를 추가합니다.")
    async def 메뉴추가(self, interaction:discord.Interaction, new_menu: str):
        await interaction.response.defer(ephemeral=True)

        self.menus.append(new_menu)
        await interaction.followup.send(content=f"'{new_menu}' 메뉴가 추천 리스트에 추가되었습니다.", ephemeral=True)

class FishingView(discord.ui.View):
    def __init__(self, fish_list):
        super().__init__(timeout=None)
        self.fish_list = fish_list

    @discord.ui.button(label="낚싯줄 당기기", style=discord.ButtonStyle.primary)
    async def pull_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        caught_fish = random.choice(self.fish_list)
        if random.random() < 0.75:  # 75% 확률로 성공
            await interaction.followup.send(f"낚시 성공! '{caught_fish}'을(를) 잡았습니다!", ephemeral=True)
        else:
            await interaction.followup.send("낚시 실패: 찌를 올렸지만 아무 것도 없었다...", ephemeral=True)
        await interaction.message.delete()

async def setup(bot: commands.Bot) -> None: 
    await bot.add_cog(GameCog(bot))
