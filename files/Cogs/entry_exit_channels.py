import sys
import os
import subprocess

import discord
from discord.ext import commands
from discord import app_commands, Permissions
from discord.ui import Modal, TextInput, Button, View, Select

from files.rw_json import json_files
from files.log import setup_logging, handle_exception

'''
    /입장 채널 설정
    /퇴장 채널 설정
    /입장 메시지 설정
    /퇴장 메시지 설정
    /입장 역할 설정

'''

class entry_exit_content_modals(Modal):
    def __init__(self, bot: commands.Bot, title, logger, *args, **kwargs):
        super().__init__(title=f"{title} 메시지 설정", *args, **kwargs)

        self.bot = bot
        self.title = title
        self.logger = logger

        self.add_item(TextInput(
            label="내용",
            style=discord.TextStyle.long,
            placeholder="내용을 입력해 주세요."
        ))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user
        
        await interaction.followup.send(content=f"{self.title} 메시지 설정을 완료했습니다. \n\n{str(self.children[0].value).replace('{member}', f'{member.mention}')}", ephemeral=True)
        if self.title == "입장":
            json_files.entry_exit_channels["entry_message"] = str(self.children[0].value)
            json_files.write_json("entry_exit_channels", json_files.entry_exit_channels)
        else:
            json_files.entry_exit_channels["exit_message"] = str(self.children[0].value)
            json_files.write_json("entry_exit_channels", json_files.entry_exit_channels)

class entry_exit_channels_modules(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.logger = setup_logging()
        sys.excepthook = handle_exception

        self.entry_channel = None
        self.exit_channel = None
        self.entry_role = []

    @commands.Cog.listener()
    async def on_ready(self):
        if json_files.entry_exit_channels["entry_channel_id"] is not None:
            try:
                self.entry_channel = self.bot.get_channel(int(json_files.entry_exit_channels["entry_channel_id"]))
            except:
                self.logger.warning("/입장 채널 설정 명령어를 통해 입장 채널을 설정해 주세요.")
            if self.entry_channel is not None:
                self.logger.info(f"입장 채널을 <{self.entry_channel.name}> 으로 설정했습니다.")
            else:
                self.logger.warning("/입장 채널 설정 명령어를 통해 입장 채널을 설정해 주세요.")
        else:
            self.logger.warning("/입장 채널 설정 명령어를 통해 입장 채널을 설정해 주세요.")

        if json_files.entry_exit_channels["exit_channel_id"] is not None:
            try:
                self.exit_channel = self.bot.get_channel(int(json_files.entry_exit_channels["exit_channel_id"]))
            except:
                self.logger.warning("/퇴장 채널 설정 명령어를 통해 퇴장 채널을 설정해 주세요.")
            if self.exit_channel is not None:
                self.logger.info(f"퇴장 채널을 <{self.exit_channel.name}> 으로 설정했습니다.")
            else:
                self.logger.warning("/퇴장 채널 설정 명령어를 통해 퇴장 채널을 설정해 주세요.")
        else:
            self.logger.warning("/퇴장 채널 설정 명령어를 통해 퇴장 채널을 설정해 주세요.")
        
        if json_files.entry_exit_channels["entry_role"]:
            for k, v in json_files.entry_exit_channels["entry_role"].copy().items():
                entry_role_guild = await self.bot.fetch_guild(int(v))
                if entry_role_guild is not None:
                    entry_role = entry_role_guild.get_role(int(k))
                    if entry_role is not None:
                        self.entry_role.append(entry_role)

    __entry_group = app_commands.Group(name="입장", description="입장")  
    __entry_channel_group = app_commands.Group(name="채널", description="입장 채널", parent=__entry_group)
    __entry_message_group = app_commands.Group(name="메시지", description="입장 메시지", parent=__entry_group)
    __entry_role_group = app_commands.Group(name="역할", description="입장 역할", parent=__entry_group)

    __exit_group = app_commands.Group(name="퇴장", description="퇴장") 
    __exit_channel_group = app_commands.Group(name="채널", description="퇴장 채널", parent=__exit_group)
    __exit_message_group = app_commands.Group(name="메시지", description="퇴장 메시지", parent=__exit_group)

    async def confirmation_roles(self, command_name:str, member:discord.Member):
        if json_files.roles["transform_table"][command_name]:
            return True
        
        roles = member.roles
        for role in roles:
            if str(role.id) in json_files.roles["available_role_ids"]:
                return True 

    @__entry_channel_group.command(name="설정", description='입장 채널을 설정합니다.')
    @app_commands.describe(채널='채널을 선택해 주세요.')
    async def entry_channel_set_command(self, interaction: discord.Interaction, 채널:discord.TextChannel) -> None:   
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("입장 채널 설정", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        self.entry_channel = 채널
        json_files.entry_exit_channels["entry_channel_id"] = str(채널.id)
        json_files.write_json("entry_exit_channels", json_files.entry_exit_channels)

        await interaction.followup.send(f"입장 채널을 {self.entry_channel.mention}으로 설정했습니다.", ephemeral=True)
        self.logger.info(f"입장 채널 변경 : 대상ID : {interaction.user.id}, 채널ID : {self.entry_channel.id}")

    @__exit_channel_group.command(name="설정", description='퇴장 채널을 설정합니다.')
    @app_commands.describe(채널='채널을 선택해 주세요.')
    async def exit_channel_set_command(self, interaction: discord.Interaction, 채널:discord.TextChannel) -> None:   
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("퇴장 채널 설정", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        self.exit_channel = 채널
        json_files.entry_exit_channels["exit_channel_id"] = str(채널.id)
        json_files.write_json("entry_exit_channels", json_files.entry_exit_channels)

        await interaction.followup.send(f"퇴장 채널을 {self.exit_channel.mention}으로 설정했습니다.", ephemeral=True)
        self.logger.info(f"퇴장 채널 변경 : 대상ID : {interaction.user.id}, 채널ID : {self.exit_channel.id}")

    @__entry_message_group.command(name="설정", description='입장 메시지를 설정합니다.')
    async def entry_message_set_command(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        Is_available = await self.confirmation_roles("입장 메시지 설정", member)
        if not Is_available:
            await interaction.response.send_message(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        await interaction.response.send_modal(entry_exit_content_modals(self.bot, "입장", self.logger))

    @__exit_message_group.command(name="설정", description='퇴장 메시지를 설정합니다.')
    async def entry_message_set_command(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        Is_available = await self.confirmation_roles("퇴장 메시지 설정", member)
        if not Is_available:
            await interaction.response.send_message(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        await interaction.response.send_modal(entry_exit_content_modals(self.bot, "퇴장", self.logger))

    @__entry_role_group.command(name="설정", description='입장 역할을 설정합니다.')
    @app_commands.choices(옵션=[
        discord.app_commands.Choice(name="추가", value="추가"),
        discord.app_commands.Choice(name="제거", value="제거")
    ])
    @app_commands.describe(옵션='옵션을 선택해 주세요.')
    @app_commands.describe(역할='역할을 선택해 주세요.')
    async def entry_message_set_command(self, interaction: discord.Interaction, 옵션:str, 역할:discord.Role) -> None:
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("입장 역할 설정", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        if 옵션 == "추가":
            if str(역할.id) not in json_files.entry_exit_channels["entry_role"]:
                self.entry_role.append(역할)
                json_files.entry_exit_channels["entry_role"][str(역할.id)] = str(역할.guild.id)
                json_files.write_json("entry_exit_channels", json_files.entry_exit_channels)

                await interaction.followup.send(content=f"입장 역할로 {역할.mention}을 추가했습니다.", ephemeral=True)
            else:
                await interaction.followup.send(content=f"해당 역할은 이미 추가되어 있습니다.", ephemeral=True)
        else:
            if str(역할.id) not in json_files.entry_exit_channels["entry_role"]:
                await interaction.followup.send(content=f"해당 역할을 찾을 수 없습니다.", ephemeral=True)
            else:
                self.entry_role.remove(역할)
                del json_files.entry_exit_channels["entry_role"][str(역할.id)]
                json_files.write_json("entry_exit_channels", json_files.entry_exit_channels)

                await interaction.followup.send(content=f"입장 역할로 {역할.mention}을 제거했습니다.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member:discord.Member):
        if member == self.bot.user:
            return

        if self.exit_channel is not None and json_files.entry_exit_channels["exit_message"] is not None:
            try:
                await self.exit_channel.send(content=str(json_files.entry_exit_channels["exit_message"]).replace('{member}', f'{member.mention}'))
            except Exception as e:
                self.logger.warning(f"퇴장 채널을 찾을 수 없습니다. : {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        if member == self.bot.user:
            return

        if self.entry_channel is not None and json_files.entry_exit_channels["entry_message"] is not None:
            try:
                await self.entry_channel.send(content=str(json_files.entry_exit_channels["entry_message"]).replace('{member}', f'{member.mention}'))
            except Exception as e:
                self.logger.warning(f"입장 채널을 찾을 수 없습니다. : {e}")
        
        if self.entry_role:
            for Role in self.entry_role:
                await member.add_roles(Role)

async def setup(bot: commands.Bot) -> None: 
    await bot.add_cog(entry_exit_channels_modules(bot))