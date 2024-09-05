import sys
import os
import subprocess

import discord
from discord.ext import commands
from discord import app_commands, Permissions

import asyncio
import platform

from files.rw_json import json_files
from files.log import setup_logging, handle_exception

try: # gtts
    from gtts import gTTS
except:
    subprocess.check_call([sys.executable,'-m', 'pip', 'install', '--upgrade', 'gtts'])
    from gtts import gTTS

current_os = platform.system()

class TTSCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.logger = setup_logging()
        sys.excepthook = handle_exception

        self.tts_channel = None
        self.tts_queue = asyncio.Queue()

        self.is_tts_playing = False
        self.voice_channel_id = None
        
    @app_commands.command(name="tts채널설정", description="TTS를 받을 텍스트 채널을 설정합니다.")
    @app_commands.describe(channel="채널을 선택해 주세요.")
    async def set_tts_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        self.tts_channel = channel
        await interaction.followup.send(content=f"TTS 채널이 설정되었습니다: {channel.mention}", ephemeral=True)

    @app_commands.command(name="tts", description="텍스트를 음성으로 변환하여 재생합니다.")
    @app_commands.describe(text="텍스트를 입력해 주세요.")
    async def tts(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer(ephemeral=True)
        
        user_voice_channel = interaction.user.voice.channel if interaction.user.voice else None
        if user_voice_channel:
            await self.tts_queue.put((text, interaction.guild.id))
            await interaction.followup.send(f"TTS가 대기열에 추가되었습니다: {text}", ephemeral=True)

            # 대기열에서 처리되지 않고 있다면, TTS 재생 시작
            if not self.is_tts_playing:
                await self.play_tts()
        else:
            await interaction.followup.send(content="음성 채널에 연결된 상태에서 명령어를 사용해야 합니다.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if message.author.bot:
            return

        # TTS 채널에서의 메시지 처리
        if self.tts_channel is not None and message.channel.id == self.tts_channel.id:
            self.voice_channel_id = message.author.voice.channel.id if message.author.voice else None
            if self.voice_channel_id:
                await self.tts_queue.put((message.content, message.guild.id))
                await message.channel.send(f"TTS가 대기열에 추가되었습니다: {message.content}", delete_after=5)
                if not self.is_tts_playing:
                    await self.play_tts()
            else:
                await message.channel.send("음성 채널에 연결된 상태에서 메시지를 보내야 합니다.", delete_after=5)

    async def play_tts(self):
        while True:
            text, guild_id = await self.tts_queue.get()
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                self.tts_queue.task_done()
                continue

            vc = await self.get_voice_client(guild, self.voice_channel_id)
            if vc:
                if json_files.is_music_playing:
                    vc.pause()  # 노래 일시 정지
                    json_files.is_music_playing = False

                # TTS 재생
                self.is_tts_playing = True
                tts = gTTS(text=text, lang='ko')
                tts.save("tts.mp3")
                if current_os == "Windows":
                    ffmpeg_paths= os.path.join(os.path.join(os.path.join(os.getcwd(), "ffmpeg"), "bin"), "ffmpeg.exe")
                    source = await discord.FFmpegOpusAudio.from_probe("tts.mp3", method='fallback', executable=ffmpeg_paths)
                else:
                    source = await discord.FFmpegOpusAudio.from_probe("tts.mp3")
                vc.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(asyncio.create_task, self.after_tts(vc)))
                while vc.is_playing():
                    await asyncio.sleep(1)
                try:
                    os.remove("tts.mp3")
                except:
                    pass
            self.tts_queue.task_done()

    async def after_tts(self, vc:discord.VoiceClient):
        self.is_tts_playing = False
        if self.tts_queue.empty() and json_files.current_music:  # TTS 대기열이 비었고 중단된 음악이 있으면 재개
            vc.resume()
            json_files.is_music_playing = True
        elif not self.tts_queue.empty():
            await self.play_tts()
        else:
            # 10분 대기 후 연결 해제 및 대기열 초기화
            await asyncio.sleep(600)
            if vc.is_connected():
                await vc.disconnect()
            await self.reset_queues()

    async def reset_queues(self):
        while not self.tts_queue.empty():
            await self.tts_queue.get()
        json_files.current_music = None
        print("대기열이 초기화되었습니다.")

    async def get_voice_client(self, guild:discord.Guild, channel_id):
        voice_channel = discord.utils.get(guild.voice_channels, id=channel_id)
        if voice_channel:
            vc = discord.utils.get(self.bot.voice_clients, guild=guild)
            if vc is None or not vc.is_connected():
                try:
                    vc = await voice_channel.connect()
                except discord.errors.ClientException as e:
                    print(f"음성 채널에 연결할 수 없습니다: {str(e)}")
                    return None
            elif vc.channel.id != voice_channel.id:
                await vc.move_to(voice_channel)
            return vc
        return None

async def setup(bot: commands.Bot) -> None: 
    await bot.add_cog(TTSCog(bot))
