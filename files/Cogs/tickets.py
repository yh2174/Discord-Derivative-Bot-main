import sys
import os
import subprocess
from typing import Tuple

import discord
from discord.ext import commands
from discord import app_commands, Permissions
from discord.ui import Modal, TextInput, Button, View, Select

from files.rw_json import json_files
from files.log import setup_logging, handle_exception

'''
    /티켓 채널 생성
    /티켓 메시지 수정
'''
class ticket_content_modals(Modal, title="티켓 메시지 수정"):
    def __init__(self, bot: commands.Bot, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.logger = logger

        self.add_item(TextInput(
            label="내용",
            style=discord.TextStyle.long,
            placeholder="내용을 입력해 주세요."
        ))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user
        await interaction.followup.send(content=f"메시지 설정을 완료했습니다. \n\n{str(self.children[0].value).replace('{member}', f'{member.mention}')}", ephemeral=True)
        json_files.tickets["content"] = str(self.children[0].value)
        json_files.write_json("tickets", json_files.tickets)
        
class ticket_modules(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.logger = setup_logging()
        sys.excepthook = handle_exception

        self.category = None
        self.closed_category = None

    __tickets_group = app_commands.Group(name="티켓", description="티켓")  
    __tickets_channel_group = app_commands.Group(name="채널", description="티켓 채널", parent=__tickets_group)  
    __tickets_message_group = app_commands.Group(name="메시지", description="티켓 메시지", parent=__tickets_group)  

    @commands.Cog.listener()
    async def on_ready(self):
        if json_files.tickets["category_id"] is not None:
            self.category = self.bot.get_channel(int(json_files.tickets["category_id"]))
            if self.category is not None:
                self.logger.info(f"티켓 카테고리 채널을 <{self.category.name}> 으로 설정했습니다.")

        if json_files.tickets["closed_category_id"] is not None:
            self.closed_category = self.bot.get_channel(int(json_files.tickets["closed_category_id"]))
            if self.closed_category is not None:
                self.logger.info(f"종료 티켓 카테고리 채널을 <{self.closed_category.name}> 으로 설정했습니다.")

        for channel_id, embed_id in json_files.tickets["channels"].copy().items():
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
                embed_object = await channel.fetch_message(int(embed_id))

                embed, view = await self.embed_view_main(channel)
                await embed_object.edit(embed=embed ,view=view)
            except Exception as e:
                self.logger.warning(f"티켓 임베드 갱신 경고 : {e}")

    async def confirmation_roles(self, command_name:str, member:discord.Member):
        if json_files.roles["transform_table"][command_name]:
            return True
        
        roles = member.roles
        for role in roles:
            if str(role.id) in json_files.roles["available_role_ids"]:
                return True

    async def embed_view_main(self, channel:discord.TextChannel) -> Tuple[discord.Embed, View]:
        embed = discord.Embed(title="", description="문의를 종료하시려면 [🔒 문의 종료] 버튼을 눌러주세요.", color=0x000000)
        button = Button(label="🔒 문의 종료", style = discord.ButtonStyle.red)
        async def button_callback(interaction:discord.Interaction):  
            await interaction.response.defer(ephemeral=True)

            try:
                embed_object = await channel.fetch_message(int(json_files.tickets["channels"][str(channel.id)]))
                await embed_object.delete()
            except:
                pass

            if self.closed_category is None:
                self.closed_category = await interaction.guild.create_category("closed tickets")
                json_files.tickets["closed_category_id"] = str(int(self.closed_category.id))
                json_files.write_json("tickets", json_files.tickets)
                
            overwrites = {interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False)}
            await channel.edit(overwrites=overwrites, category=self.closed_category)
            await interaction.followup.send(f"{interaction.user.mention} 문의를 종료했습니다.", ephemeral=True)

            del json_files.tickets["channels"][str(channel.id)]
            json_files.write_json("tickets", json_files.tickets)
            
        button.callback = button_callback

        view = View(timeout=None)
        view.add_item(button)
        
        return embed, view

    @__tickets_channel_group.command(name="생성", description='티켓 채널을 생성합니다.')
    async def tickets_channel_create_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        Is_available = await self.confirmation_roles("티켓 채널 생성", member)
        if not Is_available:
            await interaction.followup.send(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        json_files.tickets["number"] += 1
        json_files.write_json("tickets", json_files.tickets)
        number = json_files.tickets["number"]

        channel_name = f"ticket-{number}"
        if self.category is None:
            self.category = await interaction.guild.create_category("tickets")
            json_files.tickets["category_id"] = str(int(self.category.id))
            json_files.write_json("tickets", json_files.tickets)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await self.category.create_text_channel(channel_name, overwrites=overwrites)

        if json_files.tickets["content"] is not None:
            await channel.send(content=json_files.tickets["content"].replace("{member}", f"{member.mention}"))

        embed, view = await self.embed_view_main(channel)
        message = await channel.send(embed=embed, view=view)

        json_files.tickets["channels"][str(channel.id)] = str(message.id)
        json_files.write_json("tickets", json_files.tickets)

        await interaction.followup.send(content=f"새로운 티켓 채널을 생성했습니다. : {channel.mention}", ephemeral=True)
        self.logger.info(f"새로운 티켓 채널을 생성했습니다. 대상ID : {interaction.user.id}, 채널ID : {channel.id}")

    @__tickets_message_group.command(name="수정", description='티켓 메시지를 수정합니다.')
    async def tickets_message_edit_command(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        Is_available = await self.confirmation_roles("티켓 메시지 수정", member)
        if not Is_available:
            await interaction.response.send_message(content="해당 명령어 사용에 대한 권한이 없습니다.", ephemeral=True)
            return
        
        await interaction.response.send_modal(ticket_content_modals(self.bot, self.logger))

async def setup(bot: commands.Bot) -> None: 
    await bot.add_cog(ticket_modules(bot))