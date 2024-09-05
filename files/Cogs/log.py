import sys
import os
import subprocess

from datetime import datetime
from typing import Union

import discord
from discord.ext import commands
from discord import app_commands, Permissions
from discord.ui import Modal, TextInput, Button, View, Select

from files.rw_json import json_files
from files.log import setup_logging, handle_exception

'''
    /로그 채널 설정
'''

class log_modules(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.logger = setup_logging()
        sys.excepthook = handle_exception

        self.guild_channel_update = None
        self.role_update_debounce = None
        self.member_update_debounce = None

        self.log_channels = {
            "입퇴장" : None,
            "전체로그" : None,
            "메시지" : None,
            "음성방" : None,
            "채널" : None,
            "역할" : None,
            "이름변경" : None,
            "차단" : None
        }

    @commands.Cog.listener()
    async def on_ready(self):
        for k, v in json_files.log.copy().items():
            if v is not None:
                try:
                    self.log_channels[k] = self.bot.get_channel(int(v))
                except:
                    self.logger.warning(f"/로그 채널 설정 명령어를 통해 <{k}> 로그 채널을 설정해 주세요.")
                    break
                if self.log_channels[k] is not None:
                    self.logger.info(f"로그 <{k}>의 로그 채널을 {self.log_channels[k].name}으로 설정했습니다.")
                else:
                    self.logger.warning(f"/로그 채널 설정 명령어를 통해 <{k}> 로그 채널을 설정해 주세요.")
            else:
                self.logger.warning(f"/로그 채널 설정 명령어를 통해 <{k}> 로그 채널을 설정해 주세요.")

    __log_group = app_commands.Group(name="로그", description="로그")  
    __log_channel_group = app_commands.Group(name="채널", description="로그 채널", parent=__log_group)  

    async def confirmation_roles(self, command_name:str, member:discord.Member):
        if json_files.roles["transform_table"][command_name]:
            return True
        
        roles = member.roles
        for role in roles:
            if str(role.id) in json_files.roles["available_role_ids"]:
                return True
    
    @__log_channel_group.command(name="설정", description='로그 채널을 설정합니다.')
    @app_commands.describe(로그타입='로그타입을 선택해 주세요.')
    @app_commands.choices(로그타입=[
        discord.app_commands.Choice(name="입퇴장", value="입퇴장"),
        discord.app_commands.Choice(name="전체로그", value="전체로그"),
        discord.app_commands.Choice(name="메시지", value="메시지"),
        discord.app_commands.Choice(name="음성방", value="음성방"),
        discord.app_commands.Choice(name="채널", value="채널"),
        discord.app_commands.Choice(name="역할", value="역할"),
        discord.app_commands.Choice(name="이름변경", value="이름변경"),
        discord.app_commands.Choice(name="차단", value="차단")
    ])
    @app_commands.describe(채널='해당 로그타입을 설정할 채널을 선택해 주세요.')
    async def log_channel_set_command(self, interaction: discord.Interaction, 로그타입:str, 채널:discord.TextChannel) -> None:   
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("로그 채널 설정", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        if 로그타입 not in list(self.log_channels.keys()):
            await interaction.followup.send(content=f"로그타입 보기의 선택지 중에서 선택해 주세요.", ephemeral=True)
            return
        
        self.log_channels[로그타입] = 채널
        json_files.log[로그타입] = str(채널.id)
        json_files.write_json("log", json_files.log)

        await interaction.followup.send(content=f"로그타입 <{로그타입}>의 채널을 {채널.mention}으로 설정했습니다.", ephemeral=True)
    
    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        if self.log_channels["입퇴장"] is not None:
            await self.log_channels["입퇴장"].send(content=f"[{datetime.now().replace(microsecond=0)}] 입장 : {member.display_name}({member.id})")    

        if self.log_channels["전체로그"] is not None:
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 입장 : {member.display_name}({member.id})")   

    @commands.Cog.listener()
    async def on_member_remove(self, member:discord.Member):
        if self.log_channels["입퇴장"] is not None:
            await self.log_channels["입퇴장"].send(content=f"[{datetime.now().replace(microsecond=0)}] 퇴장 : {member.display_name}({member.id})")

        if self.log_channels["전체로그"] is not None:
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 퇴장 : {member.display_name}({member.id})") 

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if message.author == self.bot.user:
            return 

        if self.log_channels["메시지"] is not None:
            await self.log_channels["메시지"].send(content=f"[{datetime.now().replace(microsecond=0)}] 메시지 전송 : {message.author.display_name}({message.author.id}), 메시지ID : {message.id}")

        if self.log_channels["전체로그"] is not None:
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 메시지 전송 : {message.author.display_name}({message.author.id}), 메시지ID : {message.id}")

    @commands.Cog.listener()
    async def on_message_delete(self, message:discord.Message):
        if self.log_channels["메시지"] is not None:
            await self.log_channels["메시지"].send(content=f"[{datetime.now().replace(microsecond=0)}] 메시지 삭제 : {message.author.display_name}({message.author.id}), 메시지ID : {message.id}")

        if self.log_channels["전체로그"] is not None:
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 메시지 삭제 : {message.author.display_name}({message.author.id}), 메시지ID : {message.id}")

    @commands.Cog.listener()
    async def on_message_edit(self, before:discord.Message, after:discord.Message):
        if before.author == self.bot.user:
            return 

        if self.log_channels["메시지"] is not None:
            await self.log_channels["메시지"].send(content=f"[{datetime.now().replace(microsecond=0)}] 메시지 수정 : {before.author.display_name}({after.author.id}), 메시지ID : {after.id}")

        if self.log_channels["전체로그"] is not None:
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 메시지 수정 : {before.author.display_name}({after.author.id}), 메시지ID : {after.id}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState):
        if self.log_channels["음성방"] is not None:
            member_name = member.display_name

            if before.channel is None and after.channel is not None:
                await self.log_channels["음성방"].send(content=f"[{datetime.now().replace(microsecond=0)}] 보이스채널 접속 : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")
                
            elif before.channel is not None and after.channel is not None and before.channel != after.channel:
                await self.log_channels["음성방"].send(content=f"[{datetime.now().replace(microsecond=0)}] 보이스채널 이전 : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")

            elif before.channel is not None and after.channel is None:
                await self.log_channels["음성방"].send(content=f"[{datetime.now().replace(microsecond=0)}] 보이스채널 끊김  : {member_name}({member.id}), 보이스채널ID : {before.channel.id}")

            if before.self_mute != after.self_mute:
                if after.self_mute:
                    await self.log_channels["음성방"].send(content=f"[{datetime.now().replace(microsecond=0)}] 마이크 음소거  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")
                else:
                    await self.log_channels["음성방"].send(content=f"[{datetime.now().replace(microsecond=0)}] 마이크 음소거 해제  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")

            if before.self_deaf != after.self_deaf:
                if after.self_deaf:
                    await self.log_channels["음성방"].send(content=f"[{datetime.now().replace(microsecond=0)}] 헤드셋 음소거  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")
                else:
                    await self.log_channels["음성방"].send(content=f"[{datetime.now().replace(microsecond=0)}] 헤드셋 음소거 해제  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")

            if before.self_stream != after.self_stream:
                if after.self_stream:
                    await self.log_channels["음성방"].send(content=f"[{datetime.now().replace(microsecond=0)}] 방송 켜짐  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")
                else:
                    await self.log_channels["음성방"].send(content=f"[{datetime.now().replace(microsecond=0)}] 방송 꺼짐  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")

        if self.log_channels["전체로그"] is not None:
            member_name = member.display_name

            if before.channel is None and after.channel is not None:
                await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 보이스채널 접속 : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")
                
            elif before.channel is not None and after.channel is not None and before.channel != after.channel:
                await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 보이스채널 이전 : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")

            elif before.channel is not None and after.channel is None:
                await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 보이스채널 끊김  : {member_name}({member.id}), 보이스채널ID : {before.channel.id}")

            if before.self_mute != after.self_mute:
                if after.self_mute:
                    await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 마이크 음소거  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")
                else:
                    await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 마이크 음소거 해제  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")

            if before.self_deaf != after.self_deaf:
                if after.self_deaf:
                    await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 헤드셋 음소거  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")
                else:
                    await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 헤드셋 음소거 해제  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")

            if before.self_stream != after.self_stream:
                if after.self_stream:
                    await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 방송 켜짐  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")
                else:
                    await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 방송 꺼짐  : {member_name}({member.id}), 보이스채널ID : {after.channel.id}")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel:discord.abc.GuildChannel):
        if self.log_channels["채널"] is not None:
            await self.log_channels["메시지"].send(content=f"[{datetime.now().replace(microsecond=0)}] 채널 생성 : {channel.guild}/{channel.name}({channel.id})")

        if self.log_channels["전체로그"] is not None:
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 채널 생성 : {channel.guild}/{channel.name}({channel.id})")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel:discord.abc.GuildChannel):
        if self.log_channels["채널"] is not None:
            await self.log_channels["메시지"].send(content=f"[{datetime.now().replace(microsecond=0)}] 채널 삭제 : {channel.guild}/{channel.name}({channel.id})")

        if self.log_channels["전체로그"] is not None:
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 채널 삭제 : {channel.guild}/{channel.name}({channel.id})")

    async def send_guild_channel_update(self, before, after):
        timestamp = datetime.now().replace(microsecond=0)
        for name in ["채널", "전체로그"]:
            if self.log_channels[name] is not None:
                await self.log_channels[name].send(content=f"[{timestamp}] 채널 업데이트 : {before.guild}/{before.name}({before.id})")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before:discord.abc.GuildChannel, after:discord.abc.GuildChannel):
        if self.guild_channel_update_debounce is not None:
            self.guild_channel_update_debounce.cancel()

        self.guild_channel_update_debounce = self.bot.loop.call_later(1, lambda: self.bot.loop.create_task(self.send_guild_channel_update(before, after)))

    @commands.Cog.listener()
    async def on_guild_role_create(self, role:discord.Role):
        if self.log_channels["역할"] is not None:
            await self.log_channels["역할"].send(content=f"[{datetime.now().replace(microsecond=0)}] 역할 생성 : {role.name}({role.id})")
        
        if self.log_channels["전체로그"] is not None:
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 역할 생성 : {role.name}({role.id})")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role:discord.Role):
        if self.log_channels["역할"] is not None:
            await self.log_channels["역할"].send(content=f"[{datetime.now().replace(microsecond=0)}] 역할 삭제 : {role.name}({role.id})")

        if self.log_channels["전체로그"] is not None:
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 역할 삭제 : {role.name}({role.id})")

    async def send_role_update(self, before, after):
        timestamp = datetime.now().replace(microsecond=0)
        for name in ["역할", "전체로그"]:
            if self.log_channels[name] is not None:
                await self.log_channels[name].send(content=f"[{timestamp}] 역할 업데이트 : {before.name}({before.id})")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before:discord.Role, after:discord.Role):
        if self.role_update_debounce is not None:
            self.role_update_debounce.cancel()

        self.role_update_debounce = self.bot.loop.call_later(1, lambda: self.bot.loop.create_task(self.send_role_update(before, after)))

    async def send_member_update(self, before, after):
        before_member_name = before.display_name
        for name in ["이름변경", "전체로그"]:
            if self.log_channels[name] is not None:
                await self.log_channels["이름변경"].send(content=f"[{datetime.now().replace(microsecond=0)}] 멤버 업데이트 : {before_member_name}({after.id})")   

    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member):
        if self.member_update_debounce is not None:
            self.member_update_debounce.cancel()

        self.member_update_debounce = self.bot.loop.call_later(1, lambda: self.bot.loop.create_task(self.send_member_update(before, after)))

    @commands.Cog.listener()
    async def on_member_ban(self, guild:discord.Guild, user:Union[discord.User, discord.Member]):
        if self.log_channels["차단"] is not None:
            member_name = user.display_name
            await self.log_channels["차단"].send(content=f"[{datetime.now().replace(microsecond=0)}] 멤버 밴 : {guild.name}({guild.id}) / {member_name}({user.id})")   

        if self.log_channels["전체로그"] is not None:
            member_name = user.display_name
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 멤버 밴 : {guild.name}({guild.id}) / {member_name}({user.id})") 

    @commands.Cog.listener()
    async def on_member_unban(self, guild:discord.Guild, user:Union[discord.User, discord.Member]):
        if self.log_channels["차단"] is not None:
            member_name = user.display_name
            await self.log_channels["차단"].send(content=f"[{datetime.now().replace(microsecond=0)}] 멤버 밴 취소 : {guild.name}({guild.id}) / {member_name}({user.id})")   

        if self.log_channels["전체로그"] is not None:
            member_name = user.display_name
            await self.log_channels["전체로그"].send(content=f"[{datetime.now().replace(microsecond=0)}] 멤버 밴 취소 : {guild.name}({guild.id}) / {member_name}({user.id})")   

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        pass
    
async def setup(bot: commands.Bot) -> None: 
    await bot.add_cog(log_modules(bot))