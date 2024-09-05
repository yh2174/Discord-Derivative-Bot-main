import sys
import os
import subprocess

from collections import defaultdict
import asyncio
import time

import discord
from discord.ext import commands, tasks
from discord import app_commands, Permissions
from discord.ui import Modal, TextInput, Button, View, Select

from files.rw_json import json_files
from files.log import setup_logging, handle_exception

'''
    /레벨 채널 설정
    /레벨 역할 설정
    /레벨 확인
'''

'''
    /레벨 역할 지정 -> 필수
        - [1~5], [5~10] [10~20] [20~30] [30~40] [40~50] [51]
'''

class level_modules(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.logger = setup_logging()
        sys.excepthook = handle_exception


        self.max_level = 51
        self.switch = False
        self.roles = {
            "5" : None,
            "10" : None,
            "20" : None,
            "30" : None,
            "40" : None,
            "50" : None,
            "51" : None
        }
        self.replace_roles_name = {
            "5" : "1~4 레벨 구간",
            "10" : "5~10 레벨 구간",
            "20" : "11~20 레벨 구간",
            "30" : "21~30 레벨 구간",
            "40" : "31~40 레벨 구간",
            "50" : "41~50 레벨 구간",
            "51" : "51 레벨",
        }
        
        self.level_notify = None
        self.user_message_times = {}

        self.user_voice_status = defaultdict(lambda: {'in_channel': False, 'channel_id': None}) # 유저별 보이스 채널 접속 여부를 저장하기 위한 딕셔너리

    @commands.Cog.listener()
    async def on_ready(self):
        for key, value in json_files.level["role"].items():
            role_id = value.get("role_id")
            guild_id = value.get("guild_id")
            
            if guild_id is not None and role_id is not None:
                try:
                    guild = self.bot.get_guild(int(guild_id))
                    role = guild.get_role(int(role_id))

                    self.roles[key] = role

                except Exception as e:
                    self.logger.warning(f"역할 {self.replace_roles_name[key]}를 다시 지정해야 합니다. : {e}")

        if json_files.level["channel_id"] is not None:
            self.level_notify = self.bot.get_channel(int(json_files.level["channel_id"]))
            self.logger.info(f"레벨 채널을 {self.level_notify}으로 설정했습니다.")
        else:
            self.logger.warning("/레벨 채널 설정 명령어를 통해 레벨 채널을 지정해 주세요.")

        unassigned_roles = await self.unassigned_roles()
        none_string = ""
        for key in unassigned_roles:
            none_string += f"{self.replace_roles_name[key]}\n"
        
        if none_string != "":
            self.logger.warning(f"========================\n다음 역할을 지정해야 합니다.\n/레벨 역할 설정 명령어를 통해 역할을 지정해 주세요.\n{none_string}")
        else:
            self.switch = True
        self.give_points.start()
        
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                members = voice_channel.members
                for member in members:
                    self.user_voice_status[member.id] = {'in_channel': True, 'channel_id': voice_channel.id}

    async def exp_calculate(self, level):
        if level < 5:
            return 30
        elif level < 10:
            return 60
        elif level < 20:
            return 100
        elif level < 30:
            return 170
        elif level < 40:
            return 210
        elif level < 50:
            return 300
        else: # 51 레벨
            return 0          

    async def unassigned_roles(self):
        unassigned_role_list = []
        for k, v in self.roles.items():
            if v is None:
                unassigned_role_list.append(k)
        return unassigned_role_list
    
    async def give_role(self, user_id: str, level, channel_id):
        try:
            channel = await self.bot.fetch_channel(int(channel_id))
            member = await channel.guild.fetch_member(int(user_id))
        except Exception as e:
            self.logger.warning(f"멤버를 찾을 수 없습니다. : {e}")
            return

        if str(member.id) != user_id:
            return

        roles_to_remove = []
        role_to_add = None

        if 1 <= level < 5:
            role_to_add = self.roles["5"]
            roles_to_remove.extend([self.roles["10"], self.roles["20"], self.roles["30"], self.roles["40"], self.roles["50"], self.roles["51"]])
        elif 5 <= level < 10:
            role_to_add = self.roles["10"]
            roles_to_remove.extend([self.roles["5"], self.roles["20"], self.roles["30"], self.roles["40"], self.roles["50"], self.roles["51"]])
        elif 10 <= level < 20:
            role_to_add = self.roles["20"]
            roles_to_remove.extend([self.roles["5"], self.roles["10"], self.roles["30"], self.roles["40"], self.roles["50"], self.roles["51"]])
        elif 20 <= level < 30:
            role_to_add = self.roles["30"]
            roles_to_remove.extend([self.roles["5"], self.roles["10"], self.roles["20"], self.roles["40"], self.roles["50"], self.roles["51"]])
        elif 30 <= level < 40:
            role_to_add = self.roles["40"]
            roles_to_remove.extend([self.roles["5"], self.roles["10"], self.roles["20"], self.roles["30"], self.roles["50"], self.roles["51"]])
        elif 40 <= level < 50:
            role_to_add = self.roles["50"]
            roles_to_remove.extend([self.roles["5"], self.roles["10"], self.roles["20"], self.roles["30"], self.roles["40"], self.roles["51"]])
        else:  # 51 레벨
            role_to_add = self.roles["51"]
            roles_to_remove.extend([self.roles["5"], self.roles["10"], self.roles["20"], self.roles["30"], self.roles["40"], self.roles["50"]])

        for role in roles_to_remove:
            try:
                await member.remove_roles(role)
            except Exception as e:
                self.logger.warning(f"역할 제거 실패 : {role} from {member.name}: {e}")

        if role_to_add:
            try:
                await member.add_roles(role_to_add)
            except Exception as e:
                print(f"역할 추가 실패 : {role_to_add} to {member.name}: {e}")

        return

    async def add_experience(self, user_id:str, points:int, channel_id):
        try:
            json_files.level["user_data"][user_id]["exp"] += points
        except:
            return
        json_files.write_json("level", json_files.level)
        exp_need_point = await self.exp_calculate(json_files.level["user_data"][user_id]["level"])

        while json_files.level["user_data"][user_id]["exp"] >= exp_need_point and json_files.level["user_data"][user_id]["level"] < self.max_level:
            
            json_files.level["user_data"][user_id]["exp"] -= exp_need_point
            json_files.level["user_data"][user_id]["level"] += 1
            json_files.write_json("level", json_files.level)
            await self.give_role(user_id, json_files.level["user_data"][user_id]["level"], channel_id)
            await self.send_level_up_message(user_id)

            exp_need_point = await self.exp_calculate(json_files.level["user_data"][user_id]["level"])
            
            if json_files.level["user_data"][user_id]["level"] == self.max_level:
                json_files.level["user_data"][user_id]["exp"] = 0
                json_files.write_json("level", json_files.level)

    async def send_level_up_message(self, user_id):
        if self.level_notify is not None:
            member = self.bot.get_user(int(user_id))
            level = json_files.level["user_data"][str(user_id)]["level"]
            string = f"{member.mention}님이 **{level}레벨**을 달성했어요!"
            if level in [5, 10, 20, 30, 40, 50, 51]:
                level_object:discord.Role = self.roles[str(level)]
                string += f"\n\n{level_object.mention} 역할을 지급했어요!"

            embed = discord.Embed(title="레벨 업!", description=f"{string}", color=0x00e8ff)
            embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.display_avatar)
            await self.level_notify.send(embed=embed)

    async def subtract_experience(self, user_id:str, points:int, channel_id):
        json_files.level["user_data"][user_id]["exp"] -= points
        json_files.write_json("level", json_files.level)
        if json_files.level["user_data"][user_id]["exp"] < 0:
            while json_files.level["user_data"][user_id]["exp"] < 0 and json_files.level["user_data"][user_id]["level"] > 1:
                exp_need_point = await self.exp_calculate(json_files.level["user_data"][user_id]["level"])

                json_files.level["user_data"][user_id]["level"] -= 1
                json_files.write_json("level", json_files.level)
                await self.give_role(user_id, json_files.level["user_data"][user_id]["level"], channel_id)

                json_files.level["user_data"][user_id]["exp"] += exp_need_point
                json_files.write_json("level", json_files.level)

                if json_files.level["user_data"][user_id]["level"] == 1:
                    json_files.level["user_data"][user_id]["exp"] = 0
                    json_files.write_json("level", json_files.level)
                    break
    
    async def create_json(self, user_id, channel_id):
        if str(user_id) not in json_files.level["user_data"]:
            json_files.level["user_data"][str(user_id)] = {
                "exp" : 0,
                "level" : 1
            }
            json_files.write_json("level", json_files.level)
            await self.give_role(user_id, json_files.level["user_data"][user_id]["level"], channel_id)

    __level_group = app_commands.Group(name="레벨", description="레벨")  
    __level_channel_group = app_commands.Group(name="채널", description="레벨 채널", parent=__level_group)  
    __level_role_group = app_commands.Group(name="역할", description="레벨 역할", parent=__level_group)  

    async def confirmation_roles(self, command_name:str, member:discord.Member):
        if json_files.roles["transform_table"][command_name]:
            return True
        
        roles = member.roles
        for role in roles:
            if str(role.id) in json_files.roles["available_role_ids"]:
                return True
    
    @__level_channel_group.command(name="설정", description='레벨을 확인할 채널을 설정합니다.')
    @app_commands.describe(채널='해당 로그타입을 설정할 채널을 선택해 주세요.')
    async def level_channel_set_command(self, interaction: discord.Interaction,  채널:discord.TextChannel) -> None:  
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("레벨 채널 설정", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        self.level_notify = 채널
        json_files.level["channel_id"] = str(채널.id)
        json_files.write_json("level", json_files.level)

        await interaction.followup.send(content=f"레벨 채널을 {채널.mention}으로 설정했습니다.", ephemeral=True)

    @__level_role_group.command(name="설정", description='레벨 별 역할을 지정합니다.')
    @app_commands.choices(레벨구간=[
        discord.app_commands.Choice(name="1~4 레벨 구간", value="5"),    
        discord.app_commands.Choice(name="5~10 레벨 구간", value="10"),
        discord.app_commands.Choice(name="11~20 레벨 구간", value="20"),
        discord.app_commands.Choice(name="21~30 레벨 구간", value="30"),
        discord.app_commands.Choice(name="31~40 레벨 구간", value="40"),
        discord.app_commands.Choice(name="41~50 레벨 구간", value="50"),
        discord.app_commands.Choice(name="51 레벨", value="51")
    ])
    @app_commands.describe(레벨구간='레벨 구간을 지정해 주세요.')
    @app_commands.describe(역할='해당 로그타입을 설정할 채널을 선택해 주세요.')
    async def level_role_set_command(self, interaction: discord.Interaction, 레벨구간:str,  역할:discord.Role) -> None:  
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("레벨 역할 설정", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        if 레벨구간 not in list(self.roles.keys()):
            await interaction.followup.send(content="<레벨구간>의 보기 중에서 선택해 주세요.", ephemeral=True)
            return

        self.roles[레벨구간] = 역할
        json_files.level["role"][레벨구간]["role_id"] = str(역할.id)
        json_files.level["role"][레벨구간]["guild_id"] = str(역할.guild.id)
        json_files.write_json("level", json_files.level)

        embed = discord.Embed(title="역할 지정 완료", description="", color=0x00e8ff)
        embed.add_field(name="레벨 구간", value=f"{self.replace_roles_name[레벨구간]}", inline=True)
        embed.add_field(name="역할", value=f"{역할.mention}", inline=True)

        unassigned_roles = await self.unassigned_roles()
        if unassigned_roles:
            none_string = ""
            for idx, key in enumerate(unassigned_roles, start=1):
                none_string += f"{idx}. {self.replace_roles_name[key]}\n"
            embed.add_field(name="지정이 안된 역할 목록", value=f"다음 역할이 지정되어야 봇이 작동합니다.\n이 항목이 뜨지 않는다면 봇이 작동 중입니다.\n{none_string}", inline=False)
        else:
            self.switch = True

        await interaction.followup.send(embed=embed, ephemeral=True)

    @__level_group.command(name="확인", description='나의 레벨을 확인합니다.')
    async def level_check_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)

        if user_id not in json_files.level["user_data"]:
            await interaction.followup.send("유저 정보를 찾을 수 없습니다.", ephemeral=True)
            return
        
        now_level = json_files.level["user_data"][user_id]['level']
        if now_level == 51:
            exp_percentage = 0
        else:
            now_exp = json_files.level["user_data"][user_id]['exp']
            exp_need_point = await self.exp_calculate(now_level)
            exp_percentage = int(now_exp/exp_need_point * 100)

        embed = discord.Embed(title="", description=f"### {interaction.user.nick if interaction.user.nick is not None else interaction.user.display_name}님의 레벨 정보입니다. \n\n**lv.{now_level} ({exp_percentage}%)**", color=0x00e8ff)
        embed.set_author(name=interaction.user.nick if interaction.user.nick is not None else interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar is not None else interaction.user.default_avatar.url)
        await interaction.followup.send(embed=embed)

    @tasks.loop(minutes=1)
    async def give_points(self):
        if self.switch:
            for user_id, status in self.user_voice_status.copy().items():
                if status['in_channel']:
                    channel_id = status['channel_id']
                    points = 1
                    await self.add_experience(str(user_id), points, channel_id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState):
        if member == self.bot.user:
            return

        if before.channel and not after.channel: # 보이스 채널에서 나갔을 떼
            self.user_voice_status[member.id] = {'in_channel': False, 'channel_id': None}

        elif not before.channel and after.channel: # 보이스 채널을 접속했을 때
            await self.create_json(str(member.id), after.channel.id)
            self.user_voice_status[member.id] = {'in_channel': True, 'channel_id': after.channel.id}

        elif (before.channel and after.channel and before.channel != after.channel): # 보이스 채널을 이전했을 때
            await self.create_json(str(member.id), after.channel.id)
            self.user_voice_status[member.id] = {'in_channel': False, 'channel_id': None}
            await asyncio.sleep(0.2)
            self.user_voice_status[member.id] = {'in_channel': True, 'channel_id': after.channel.id}
    
    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if message.author == self.bot.user:
            return
        
        user_id = message.author.id
        current_time = time.time()

        if user_id not in self.user_message_times:
            self.user_message_times[user_id] = []

        self.user_message_times[user_id].append(current_time)

        self.user_message_times[user_id] = [t for t in self.user_message_times[user_id] if t > current_time - 5]
        
        await self.create_json(str(message.author.id), message.channel.id)
        if self.switch:
            if len(self.user_message_times[user_id]) > 5:
                await message.delete()

                # 점수 삭감
                await self.subtract_experience(str(user_id), 25, message.channel.id)
            else:
                # 점수 증가
                await self.add_experience(str(user_id), 5, message.channel.id)

        
async def setup(bot: commands.Bot) -> None: 
    await bot.add_cog(level_modules(bot))