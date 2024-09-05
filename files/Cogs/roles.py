import sys
import os
import subprocess

import re
from datetime import datetime
from typing import List

import discord
from discord.ext import commands
from discord import app_commands, Permissions
from discord.ui import Modal, TextInput, Button, View, Select

from files.rw_json import json_files
from files.log import setup_logging, handle_exception

try: # emoji
    import emoji
except:
    subprocess.check_call([sys.executable,'-m', 'pip', 'install', '--upgrade', 'emoji'])
    import emoji

try: # BackgroundScheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except:
    subprocess.check_call([sys.executable,'-m', 'pip', 'install', '--upgrade', 'apscheduler'])
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

class scheduler_main():
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.sched = BackgroundScheduler()
        self.sched.start()

    async def delete_json_data(self, time:datetime, message:str, channel:discord.TextChannel):
        for idx, json_value in enumerate(json_files.role_payouts["message_sch"][:]):
            if json_value is not None and json_value["datetime"] == str(time) and json_value["message"] == str(message) and json_value["channel_id"] == str(channel.id):
                json_files.role_payouts["message_sch"][idx] = None
                json_files.write_json("role_payouts", json_files.role_payouts)

    async def send_message(self, time:datetime, message:str, channel:discord.TextChannel):
        await channel.send(message)
        await self.delete_json_data(time, message, channel)

    async def create_schedules(self, time:datetime, message:str, channel:discord.TextChannel):
        self.sched.add_job(lambda: self.bot.loop.create_task(self.send_message(time, message, channel)), 'date', run_date=time)

'''
    /역할지급
    /역할 삭제
    /역할 지급 채널
    /역할 지급 메세지
    /역할 지급 이모지
    /역할 이모지 제거
    /닉네임 변경
    /메세지스케줄
'''

class role_content_modals(Modal, title="역할 지급 메시지 수정"):
    def __init__(self, bot: commands.Bot, logger, self_client, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.logger = logger
        self.self_client:role_modules = self_client

        self.add_item(TextInput(
            label="내용",
            style=discord.TextStyle.long,
            placeholder="내용을 입력해 주세요."
        ))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        await interaction.followup.send(content=f"메시지 설정을 완료했습니다. \n\n{str(self.children[0].value)}", ephemeral=True)
        json_files.role_payouts["message"] = str(self.children[0].value)
        json_files.write_json("role_payouts", json_files.role_payouts)

        await self.self_client.message_edit()

class message_scheduling_modals(Modal, title="메시지 스케줄"):
    def __init__(self, bot: commands.Bot, logger, channel:discord.TextChannel, sched, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.logger = logger
        self.channel = channel
        self.sched:scheduler_main = sched

        self.add_item(TextInput(
            label="날짜",
            style=discord.TextStyle.short,
            placeholder=f"날짜를 입력합니다. 예시) 2024-01-01"
        )),
        self.add_item(TextInput(
            label="시간",
            style=discord.TextStyle.short,
            placeholder=f"시간을 입력합니다. 예시) 20:00"
        )),
        self.add_item(TextInput(
            label="내용",
            style=discord.TextStyle.long,
            placeholder="내용을 입력해 주세요."
        ))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        time_bool, time_String = await self.time_pattern(self.children[0].value, self.children[1].value)
        if not time_bool:
            await interaction.followup.send(content=time_String, ephemeral=True)
            return
        
        real_time = await self.convert_to_realtime(self.children[0].value, self.children[1].value)
        Future = await self.is_Future(real_time)
        if not Future:
            await interaction.followup.send(content="현재 시간보다 과거 시간을 선택할 수 없습니다.", ephemeral=True)
            return
        
        member = interaction.user
        await interaction.followup.send(content=f"메시지 스케줄을 완료했습니다. \n\n실행 시간 : {str(real_time)}\n\n{str(self.children[2].value).replace('{member}', f'{member.mention}')}", ephemeral=True)
        json_files.role_payouts["message_sch"].append({
            "datetime" : str(real_time),
            "message" : str(self.children[2].value),
            "channel_id" : str(self.channel.id)
        })
        json_files.write_json("role_payouts", json_files.role_payouts)
        await self.sched.create_schedules(real_time, str(self.children[2].value), self.channel)

    async def is_Future(self, time: datetime):
        now_datetime = datetime.now().replace(microsecond=0)

        if now_datetime < time:
            return True
        else:
            return False

    async def convert_to_realtime(self, date_str:str, time_str:str):
        real_time = datetime.strptime(f"{str(date_str)} {str(time_str)}", "%Y-%m-%d %H:%M")
        return real_time  

    async def time_pattern(self, input_date:str, input_time:str):
        ''' 닐짜 및 시간을 받아 양식이 일치한지 검사 '''

        if not bool(re.match(r'\d{4}-\d{2}-\d{2}', str(input_date))):
            return False, "날짜 양식이 틀렸습니다. 양식에 맞춰 다시 입력해주세요. (YYYY-MM-DD)"
        
        if not bool(re.match(r'^(?:[01]\d|2[0-3]):[0-5]\d$', str(input_time))):
            return False, "시간 양식이 틀렸습니다. 양식에 맞춰 다시 입력해주세요. HH:MM"

        return True, None

    async def create_time_format(self, time:datetime):
        weekdays_list = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        weekday = weekdays_list[time.weekday()]
        ampm = "오후" if time.hour >= 12 else "오전"
        hours = time.hour % 12 if time.hour % 12 != 0 else 12

        return f"{time.year}년 {time.month:02}월 {time.day:02}일 {weekday} {ampm} {hours}시 {time.minute:02}분"

class role_modules(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.sched = scheduler_main(self.bot)

        self.logger = setup_logging()
        sys.excepthook = handle_exception

        self.channel = None

    __role_group = app_commands.Group(name="역할", description="역할")  
    __role_payouts_group = app_commands.Group(name="지급", description="역할 지급", parent=__role_group)  
    __role_emoji_group = app_commands.Group(name="이모지", description="역할 이모지", parent=__role_group)  

    __nickname_group = app_commands.Group(name="닉네임", description="닉네임")  

    @commands.Cog.listener()
    async def on_ready(self):
        if json_files.role_payouts["channel_id"] is not None:
            try:
                self.channel = self.bot.get_channel(int(json_files.role_payouts["channel_id"]))
            except:
                self.logger.warning("/역할 지급 채널 명령어를 통해 역할 지급 채널을 설정해 주세요.")
            if self.channel is not None:
                self.logger.info(f"역할 지급 채널을 <{self.channel.name}> 으로 설정했습니다.")
                await self.message_edit()
            else:
                self.logger.warning("/역할 지급 채널 명령어를 통해 역할 지급 채널을 설정해 주세요.")
        else:
            self.logger.warning("/역할 지급 채널 명령어를 통해 역할 지급 채널을 설정해 주세요.")


        for idx, json_value in enumerate(json_files.role_payouts["message_sch"][::-1]):
            if json_value is not None:
                real_idx = len(json_files.role_payouts["message_sch"]) - 1 - idx

                time_object = datetime.strptime(json_value["datetime"], '%Y-%m-%d %H:%M:%S')
                now_datetime = datetime.now().replace(microsecond=0)

                if now_datetime < time_object:
                    channel = self.bot.get_channel(int(json_value["channel_id"]))
                    if channel is not None:
                        await self.sched.create_schedules(time_object, json_value["message"], channel)
                    else:
                        json_files.role_payouts["message_sch"][real_idx] = None
                        json_files.write_json("role_payouts", json_files.role_payouts)
                else:
                    json_files.role_payouts["message_sch"][real_idx] = None
                    json_files.write_json("role_payouts", json_files.role_payouts)

    async def confirmation_roles(self, command_name:str, member:discord.Member):
        if json_files.roles["transform_table"][command_name]:
            return True
        
        roles = member.roles
        for role in roles:
            if str(role.id) in json_files.roles["available_role_ids"]:
                return True
    
    async def message_edit(self):
        if json_files.role_payouts["message"] is not None:
            embed = discord.Embed(title="", description=json_files.role_payouts["message"], color=0x000000)

            view = View(timeout=None)
            for idx, (k, v) in enumerate(json_files.role_payouts["emoji"].items()): 
                callback_function = lambda i, index=v: button_callback(i, index)
                globals()['market_buy_button{}'.format(str(idx))] = Button(emoji=k, style=discord.ButtonStyle.blurple)
                globals()['market_buy_button{}'.format(str(idx))].callback = callback_function
                view.add_item(globals()['market_buy_button{}'.format(str(idx))])

            async def button_callback(interaction: discord.Interaction, value):
                await interaction.response.defer(ephemeral=True)
                Role = None
                Role = interaction.guild.get_role(int(value))
                if Role is not None:
                    await interaction.user.add_roles(Role)
                    await interaction.followup.send(content=f"{Role.mention} 역할을 지급했습니다.", ephemeral=True)

            if json_files.role_payouts["embed_id"] is None:
                message = await self.channel.send(embed=embed, view=view)
                json_files.role_payouts["embed_id"] = str(message.id)
                json_files.write_json("role_payouts", json_files.role_payouts)
            else:
                message_object = await self.channel.fetch_message(int(json_files.role_payouts["embed_id"]))
                await message_object.edit(embed=embed, view=view)

    @app_commands.command(name="역할지급", description='역할을 지급합니다.')
    @app_commands.describe(대상='대상을 선택해 주세요.')
    @app_commands.describe(역할='지급할 역할을 선택해 주세요.')
    async def role_payouts_command(self, interaction: discord.Interaction, 대상:discord.Member, 역할:discord.Role) -> None:
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("역할지급", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        await 대상.add_roles(역할)
        await interaction.followup.send(content=f"{대상.mention}에게 {역할.mention} 역할을 지급했습니다.", ephemeral=True)

    @__role_group.command(name="삭제", description='역할을 제거합니다.')
    @app_commands.describe(대상='대상을 선택해 주세요.')
    @app_commands.describe(역할='제거할 역할을 선택해 주세요.')
    async def role_delete_command(self, interaction: discord.Interaction, 대상:discord.Member, 역할:discord.Role) -> None:
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("역할 삭제", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        roles = 대상.roles
        if 역할 not in roles:
            await interaction.followup.send(content=f"{대상.mention}(은)는 {역할.mention} 역할을 보유하고 있지 않습니다.", ephemeral=True)
            return
        
        await 대상.remove_roles(역할)
        await interaction.followup.send(content=f"{대상.mention}에게서 {역할.mention} 역할을 제거했습니다.", ephemeral=True)

    @__role_payouts_group.command(name="채널", description='역할 지급 채널을 지정합니다.')
    @app_commands.describe(채널='역할 지급 채널을 선택해 주세요.')
    async def role_payouts_channel_command(self, interaction: discord.Interaction, 채널:discord.TextChannel) -> None:
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("역할 지급 채널", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        self.channel = 채널
        json_files.role_payouts["embed_id"] = None
        json_files.role_payouts["channel_id"] = str(채널.id)
        json_files.write_json("role_payouts", json_files.role_payouts)
        await interaction.followup.send(content=f"역할 지정 채널을 {채널.mention}으로 설정했습니다.", ephemeral=True)
        
        await self.message_edit()

    @__role_payouts_group.command(name="메세지", description='역할 지급 임베드에 출력할 메시지를 입력합니다.')
    async def role_payouts_message_command(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        Is_available = await self.confirmation_roles("역할 지급 메세지", member)
        if not Is_available:
            await interaction.response.send_message(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        await interaction.response.send_modal(role_content_modals(self.bot, self.logger, self))

    @__role_payouts_group.command(name="이모지", description='역할 지급 임베드에 이모지 버튼 및 역할을 추가합니다.')
    @app_commands.describe(이모지='이모지를 입력해 주세요.')
    @app_commands.describe(역할='지급할 역할을 선택해 주세요.')
    async def role_payouts_emoji_command(self, interaction: discord.Interaction, 이모지:str, 역할:discord.Role) -> None:
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("역할 지급 이모지", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        if not emoji.is_emoji(이모지):
            await interaction.followup.send(content=f"입력하신 {이모지}(은)는 이모지가 아니므로 명령어 사용을 취소합니다.", ephemeral=True)
            return

        json_files.role_payouts["emoji"][이모지] = str(역할.id)
        json_files.write_json("role_payouts", json_files.role_payouts)
        await interaction.followup.send(content=f"{이모지}의 지정 역할을 {역할.mention}으로 설정했습니다.", ephemeral=True)
        await self.message_edit()

    async def role_emoji_remove_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        choices = list(json_files.role_payouts["emoji"].keys())
        choices = [app_commands.Choice(name=k, value=k) for k in choices if current.lower() in k.lower()][:25]
        return choices
    
    @__role_emoji_group.command(name="제거", description='역할 지급 이모지의 특정 이모지를 제거합니다.')
    @app_commands.describe(이모지='이모지를 선택해 주세요.')
    @app_commands.autocomplete(이모지=role_emoji_remove_autocomplete)
    async def role_emoji_remove_command(self, interaction: discord.Interaction, 이모지:str) -> None:
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("역할 이모지 제거", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return

        if 이모지 not in json_files.role_payouts["emoji"]:
            await interaction.followup.send("해당 이모지를 찾을 수 없습니다.", ephemeral=True)
            return
        
        del json_files.role_payouts["emoji"][이모지]
        json_files.write_json("role_payouts", json_files.role_payouts)
        await interaction.followup.send(f"{이모지}를 제거했습니다.", ephemeral=True)
        await self.message_edit()

    @__nickname_group.command(name="변경", description='대상의 닉네임을 변경합니다.')
    @app_commands.describe(대상='대상을 선택해 주세요.')
    @app_commands.describe(닉네임='변경할 이름을 선택해 주세요.')
    async def nickname_change_command(self, interaction: discord.Interaction, 대상:discord.Member, 닉네임:str) -> None:
        member = interaction.user
        Is_available = await self.confirmation_roles("닉네임 변경", member)
        if not Is_available:
            await interaction.response.send_message(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        await 대상.edit(nick=닉네임)
        await interaction.followup.send(content=f"{대상.mention}의 닉네임을 {닉네임}으로 변경했습니다.", ephemeral=True)

    @app_commands.command(name="메세지스케줄", description='메세지 스케줄을 작성합니다.')
    @app_commands.describe(채널='메시지를 출력할 채널을 선택합니다.')
    async def message_command(self, interaction: discord.Interaction, 채널:discord.TextChannel) -> None:
        member = interaction.user
        Is_available = await self.confirmation_roles("메세지스케줄", member)
        if not Is_available:
            await interaction.response.send_message(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        await interaction.response.send_modal(message_scheduling_modals(self.bot, self.logger, 채널, self.sched))
    
   
async def setup(bot: commands.Bot) -> None: 
    await bot.add_cog(role_modules(bot))