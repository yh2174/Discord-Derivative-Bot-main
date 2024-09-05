import sys

import discord
from discord.ext import commands
from discord import app_commands, Permissions

from files.rw_json import json_files
from files.log import setup_logging, handle_exception
from typing import List

'''
    /명령어 사용 역할
    /권한 예외
'''

class permissions_modules(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.logger = setup_logging()
        sys.excepthook = handle_exception
    
    __command_group = app_commands.Group(name="명령어", description="명령어", default_permissions=Permissions(administrator=True))  
    __permissions_group = app_commands.Group(name="권한", description="권한", default_permissions=Permissions(administrator=True))  

    __command_user_group = app_commands.Group(name="사용", description="명령어 사용", parent=__command_group, default_permissions=Permissions(administrator=True))  

    async def command_user_role_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        choices = list(json_files.roles["transform_table"].keys())
        choices = [app_commands.Choice(name=choice, value=choice) for choice in choices if current.lower() in choice.lower()][:25]
        return choices

    @__command_user_group.command(name="역할", description='명령어를 사용할 수 있는 역할을 설정합니다.')
    @app_commands.choices(옵션=[
        discord.app_commands.Choice(name="추가", value="추가"),
        discord.app_commands.Choice(name="제거", value="제거")
    ])
    @app_commands.describe(옵션='옵션을 선택해 주세요.')
    @app_commands.describe(역할='역할을 선택해 주세요.')
    async def command_user_role_command(self, interaction: discord.Interaction, 옵션:str, 역할:discord.Role) -> None:
        await interaction.response.defer(ephemeral=True)
        
        if 옵션 not in ["추가", "제거"]:
            await interaction.followup.send(content="<옵션>의 선택지 중에서 선택해 주세요.", ephemeral=True)
            return
        
        role_id = str(역할.id)

        if 옵션 == "추가":
            if role_id not in json_files.roles["available_role_ids"]:
                json_files.roles["available_role_ids"].append(role_id)
                json_files.write_json("roles", json_files.roles)
                await interaction.followup.send(content=f"지금부터 {역할.mention} 역할 보유자는 명령어를 사용할 수 있습니다.", ephemeral=True)
                self.logger.info(f"명령어 사용 권한 보유 역할 추가 : {역할.name}")
                return
            else:
                await interaction.followup.send(content=f"이미 {역할.mention}은 명령어 사용 가능 역할 목록에 추가되어 있습니다.", ephemeral=True)
                return
        
        else:
            if role_id in json_files.roles["available_role_ids"]:
                json_files.roles["available_role_ids"].remove(role_id)
                json_files.write_json("roles", json_files.roles)
                await interaction.followup.send(content=f"지금부터 {역할.mention} 역할 보유자는 명령어를 사용할 수 없습니다.", ephemeral=True)
                self.logger.info(f"명령어 사용 권한 보유 역할 제거 : {역할.name}")
                return
            else:
                await interaction.followup.send(content=f"{역할.mention}은 명령어 사용 가능 역할 목록에 추가되어 있지 않습니다.", ephemeral=True)
                return

    @__permissions_group.command(name="예외", description='명령어 사용 가능 역할과 무관하게 사용 가능한 명령어를 설정합니다.')
    @app_commands.choices(옵션=[
        discord.app_commands.Choice(name="켜기", value="켜기"),
        discord.app_commands.Choice(name="끄기", value="끄기")
    ])
    @app_commands.autocomplete(명령어=command_user_role_autocomplete)
    @app_commands.describe(옵션='옵션을 선택해 주세요.')
    @app_commands.describe(명령어='명령어를 선택해 주세요.')
    async def command_user_role_command(self, interaction: discord.Interaction, 옵션:str, 명령어:str) -> None:
        await interaction.response.defer(ephemeral=True)

        if (옵션 not in ["켜기", "끄기"] or 명령어 not in json_files.roles["transform_table"]):
            await interaction.followup.send(content="<옵션>의 선택지 중에서 선택해 주세요." if 옵션 not in {"켜기", "끄기"} else "<명령어>의 선택지 중에서 선택해 주세요.", ephemeral=True)
            return
        
        if 옵션 == "켜기":
            if json_files.roles["transform_table"][명령어]:
                await interaction.followup.send(content=f"이미 <{명령어}>은 모든 사용자가 사용할 수 있습니다.", ephemeral=True)
                return
            else:
                json_files.roles["transform_table"][명령어] = True
                json_files.write_json("roles", json_files.roles)
                await interaction.followup.send(content=f"지금부터 <{명령어}> 명령어는 모든 사용자가 사용할 수 있습니다.", ephemeral=True)
                self.logger.info(f"<{명령어}> 잠금 해제")
                return
        else:
            if json_files.roles["transform_table"][명령어]:
                json_files.roles["transform_table"][명령어] = False
                json_files.write_json("roles", json_files.roles)
                await interaction.followup.send(content=f"지금부터 <{명령어}> 명령어는 아무 사용자나 사용할 수 없습니다.", ephemeral=True)
                self.logger.info(f"<{명령어}> 잠금")
                return
            else:
                await interaction.followup.send(content=f"이미 <{명령어}>은 아무 사용자나 사용할 수 없습니다.", ephemeral=True)
                return

async def setup(bot: commands.Bot) -> None: 
    await bot.add_cog(permissions_modules(bot))