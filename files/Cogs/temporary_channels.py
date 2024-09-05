import sys
import os
import subprocess
import asyncio

import discord
from discord.ext import commands
from discord import app_commands, Permissions
from discord.ui import Modal, TextInput, Button, View, Select

from files.rw_json import json_files
from files.log import setup_logging, handle_exception
'''
    /임시 채널 설정
    /임시 채널 생성
    /임시 카테고리 설정

    temporary_channels
'''

class temporary_channel_modules(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.logger = setup_logging()
        sys.excepthook = handle_exception

        self.temp_channel = None
        self.temp_category = None

    __temporary_group = app_commands.Group(name="임시", description="임시")  
    __temporary_channel_group = app_commands.Group(name="채널", description="임시 채널", parent=__temporary_group)  
    __temporary_category_group = app_commands.Group(name="카테고리", description="임시 카테고리", parent=__temporary_group)  

    @commands.Cog.listener()
    async def on_ready(self):
        if json_files.temporary_channels["temporary_channel_id"] is not None:
            try:
                self.temp_channel = self.bot.get_channel(int(json_files.temporary_channels["temporary_channel_id"]))
            except:
                self.logger.warning("/임시 채널 설정 또는 /임시 채널 생성 명령어를 통해 임시 채널을 설정해 주세요.")
            if self.temp_channel is not None:
                self.logger.info(f"임시 채널을 <{self.temp_channel.name}> 으로 설정했습니다.")
            else:
                self.logger.warning("/임시 채널 설정 또는 /임시 채널 생성 명령어를 통해 임시 채널을 설정해 주세요.")
        else:
            self.logger.warning("/임시 채널 설정 또는 /임시 채널 생성 명령어를 통해 임시 채널을 설정해 주세요.")

        if json_files.temporary_channels["category_id"] is not None:
            try:
                self.temp_category = self.bot.get_channel(int(json_files.temporary_channels["category_id"]))
            except:
                self.logger.warning("/임시 카테고리 설정 명령어를 통해 임시 채널을 설정해 주세요.")
            if self.temp_category is not None:
                self.logger.info(f"임시 카테고리를 <{self.temp_category.name}> 으로 설정했습니다.")
            else:
                self.logger.warning("/임시 카테고리 설정 명령어를 통해 임시 채널을 설정해 주세요.")
        else:
            self.logger.warning("/임시 카테고리 설정 명령어를 통해 임시 채널을 설정해 주세요.")

        channels = await self.get_all_channels()
        for channel_id in channels:
            channel = self.bot.get_channel(int(channel_id))
            if channel and not channel.members:
                await self.delete_channel(channel)
            await asyncio.sleep(0.2)

# ------ [ temporary_channel ]
    async def get_all_channels(self):
        all_channel_idx = [idx for idx in json_files.temporary_channels["channel_idx"] if idx is not None]
        return all_channel_idx

    async def create_channel(self, member:discord.Member):
        ''' 임시 생성 삭제 '''
        member_name = member.nick if member.nick else member.display_name

        try:
            if self.temp_category is not None:
                voice_channel = await self.temp_category.create_voice_channel(name=f"{member_name}'s 임시채널", bitrate=96000, rtc_region='south-korea')
            else:
                voice_channel = await self.temp_channel.category.create_voice_channel(name=f"{member_name}'s 임시채널", bitrate=96000, rtc_region='south-korea')
        except Exception as e:
            self.logger.warning(f"임시 채널 생성 과정에서 오류가 발생했습니다. : {e}")
        
        if voice_channel is not None:
            json_files.temporary_channels["channel_idx"].append(str(voice_channel.id))
            json_files.write_json("temporary_channels", json_files.temporary_channels)

            await member.move_to(voice_channel)

    async def delete_channel(self, channel:discord.VoiceChannel):
        ''' 임시 채널 삭제 '''
        try:
            if str(channel.id) in json_files.temporary_channels["channel_idx"]:
                json_files.temporary_channels["channel_idx"].remove(str(channel.id))
                json_files.write_json("temporary_channels", json_files.temporary_channels)
                await channel.delete()
        except Exception as e:
            self.logger.warning(f"임시 채널 삭제 과정에서 오류가 발생했습니다. : {e}")

    async def handle_voice_state_update(self, before:discord.VoiceState, after:discord.VoiceState, member:discord.Member):
        ''' 채널 삭제 및 채널 생성 핸들링 '''

        before_channel_id = str(before.channel.id) if before.channel else None
        after_channel_id = str(after.channel.id) if after.channel else None

        temp_channel_id = str(self.temp_channel.id)
        all_channels = await self.get_all_channels()

        if before_channel_id == temp_channel_id:
            return

        if before_channel_id in all_channels and not before.channel.members:
            await self.delete_channel(before.channel)

        if after_channel_id == temp_channel_id or (before_channel_id in all_channels and after_channel_id in temp_channel_id):
            await self.create_channel(member)

    async def confirmation_roles(self, command_name:str, member:discord.Member):
        if json_files.roles["transform_table"][command_name]:
            return True
        
        roles = member.roles
        for role in roles:
            if str(role.id) in json_files.roles["available_role_ids"]:
                return True

    @__temporary_channel_group.command(name="설정", description='임시 채널로 지정할 채널을 선택합니다.')
    @app_commands.describe(보이스채널='보이스채널 선택해 주세요.')
    async def temporary_channel_set_command(self, interaction: discord.Interaction, 보이스채널:discord.VoiceChannel) -> None:
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user
        Is_available = await self.confirmation_roles("임시 채널 설정", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        if str(보이스채널.id) in json_files.temporary_channels["channel_idx"]:
            await interaction.followup.send(content="생성된 임시 채널에 대해 임시 채널로 지정할 수 없습니다.", ephemeral=True)
            return
        
        json_files.temporary_channels["temporary_channel_id"] = str(보이스채널.id)
        json_files.write_json("temporary_channels", json_files.temporary_channels)
        self.temp_channel = 보이스채널
        await interaction.followup.send(content=f"임시 채널을 {보이스채널.mention}으로 설정했습니다.", ephemeral=True)

    @__temporary_channel_group.command(name="생성", description='임시 채널을 생성합니다.')
    @app_commands.describe(이름='채널 이름을 입력해 주세요.')
    async def temporary_channel_create_command(self, interaction: discord.Interaction, 이름:str) -> None:
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user
        Is_available = await self.confirmation_roles("임시 채널 생성", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        if self.temp_category != None:
            channel = await self.temp_category.create_voice_channel(이름)
        else:
            channel = await interaction.guild.create_voice_channel(이름)

        self.temp_channel = channel
        json_files.temporary_channels["temporary_channel_id"] = str(channel.id)
        json_files.write_json("temporary_channels", json_files.temporary_channels)

        await interaction.followup.send(content=f"임시 채널을 {channel.mention}으로 설정했습니다.", ephemeral=True)

    @__temporary_category_group.command(name="설정", description='임시 카테고리를 설정합니다.')
    @app_commands.describe(카테고리='카테고리를 선택해 주세요.')
    async def temporary_channel_create_command(self, interaction: discord.Interaction, 카테고리:discord.CategoryChannel) -> None:
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("임시 카테고리 설정", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        self.temp_category = 카테고리
        json_files.temporary_channels["category_id"] = str(카테고리.id)
        json_files.write_json("temporary_channels", json_files.temporary_channels)

        await interaction.followup.send(content=f"임시 카테고리를 <{카테고리.name}>으로 설정했습니다.", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState):
        if self.temp_channel is not None:
            if before.channel and not after.channel:
                if len(before.channel.members) == 0:
                    await self.delete_channel(before.channel)
                
            elif not before.channel and after.channel and member != self.bot.user:
                if str(after.channel.id) == str(self.temp_channel.id):
                    await self.create_channel(member)
                
            elif (before.channel and after.channel and before.channel != after.channel):
                await self.handle_voice_state_update(before, after, member)


async def setup(bot: commands.Bot) -> None: 
    await bot.add_cog(temporary_channel_modules(bot))