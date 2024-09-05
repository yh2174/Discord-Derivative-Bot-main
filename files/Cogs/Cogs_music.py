import sys
import os
import subprocess
import yt_dlp

import discord
from discord.ext import commands
from discord import app_commands, Permissions
from discord.ui import Modal, TextInput, Button, View, Select

import asyncio
import platform
from urllib.error import HTTPError

from files.rw_json import json_files
from files.log import setup_logging, handle_exception

current_os = platform.system()

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.logger = setup_logging()
        sys.excepthook = handle_exception

        self.music_channel: discord.TextChannel | None = None
        self.music_queue = asyncio.Queue()

    @app_commands.command(name="노래채널설정", description="노래 기능을 사용할 텍스트 채널을 설정합니다.")
    async def set_music_channel(self, interaction:discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        self.music_channel = channel
        await interaction.followup.send(content=f"노래 채널이 설정되었습니다: {channel.mention}")

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        # 봇이 보낸 메시지는 무시
        if message.author.bot:
            return

        # 설정된 음악 채널이 아닌 경우 무시
        if (not self.music_channel) or (self.music_channel and message.channel.id != self.music_channel.id):
            return

        # 음악 재생 요청 처리
        await self.handle_music_request(message)

        # 메시지를 10초 후 삭제
        await asyncio.sleep(10)
        await message.delete()

    async def handle_music_request(self, message:discord.Message):
        search_query = message.content.strip()
        if not search_query:
            return

        if message.author.voice is None:
            await message.channel.send("음성 채널에 연결되어 있지 않습니다.", delete_after=10)
            return

        vc = await self.get_voice_client(message.guild, message.author.voice.channel.id)
        if vc is None:
            await message.channel.send("음성 채널에 연결할 수 없습니다.", delete_after=10)
            return

        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'quiet': True,
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'cookiefile': '/home/ubuntu/realkk/bot/cookies.txt',
                'verbose': True,  # 디버그 정보를 더 자세히 보려면 이 옵션을 추가하세요
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{search_query}", download=False)
                if not info['entries']:
                    await message.channel.send("검색 결과가 없습니다. 다른 검색어를 시도해 주세요.", delete_after=10)
                    return

                video = info['entries'][0]
                url = video['url']
                title = video['title']

                await self.music_queue.put((url, message.author.voice.channel, title))
                await message.channel.send(f"Queued: {title}", delete_after=10)

                if not json_files.is_music_playing:
                    await self.play_next_song(message)

                await self.send_queue_to_user(message)

        except yt_dlp.utils.DownloadError as e:
            await message.channel.send(f"yt-dlp 오류가 발생했습니다: {e}", delete_after=10)
        except Exception as e:
            await message.channel.send(f"알 수 없는 오류가 발생했습니다: {e}", delete_after=10)

    async def send_queue_to_user(self, message:discord.Message):
        # 대기열 정보를 리스트로 변환
        queue_list = list(self.music_queue._queue)
        if not queue_list:
            queue_message = "현재 대기열이 비어 있습니다."
        else:
            queue_message = "\n".join([f"{i + 1}. {item[2]}" for i, item in enumerate(queue_list)])

        # 사용자에게 대기열을 본인만 볼 수 있는 메시지로 전송
        await message.channel.send(
            f"**현재 노래 대기열:**\n{queue_message}",
            delete_after=30,
            reference=message,
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
            silent=True,
            view=MusicControlView(self)
        )

    async def play_next_song(self, ctx:discord.Message):
        if not self.music_queue.empty():
            url, voice_channel, title = await self.music_queue.get()
            vc = await self.get_voice_client(ctx.guild, voice_channel.id)

            if vc is None:
                await ctx.channel.send("음성 채널에 연결하지 못했습니다.", delete_after=10)
                return

            json_files.is_music_playing = True
            try:
                if current_os == "Windows":
                    ffmpeg_paths = os.path.join(os.path.join(os.path.join(os.getcwd(), "ffmpeg"), "bin"), "ffmpeg.exe")
                    source = await discord.FFmpegOpusAudio.from_probe(url, method='fallback', executable=ffmpeg_paths)
                else:
                    source = await discord.FFmpegOpusAudio.from_probe(url)
                json_files.current_music = source
                vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.after_music(ctx, vc), self.bot.loop))
                await ctx.channel.send(f"Now playing: {title}", delete_after=10)
            except subprocess.CalledProcessError as e:
                await ctx.channel.send(f"FFmpeg 오류가 발생했습니다: {e}", delete_after=10)
            except Exception as e:
                await ctx.channel.send(f"음악을 재생하는 도중 오류가 발생했습니다: {e}", delete_after=10)

        else:
            vc = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
            if vc:
                await vc.disconnect()
                json_files.is_music_playing = False
                await self.reset_queues()

    async def after_music(self, ctx:discord.Message, vc):
        await asyncio.sleep(1)  # 짧은 대기 시간 추가
        if vc.is_playing():
            return  # 여전히 재생 중이면 함수 종료

        json_files.is_music_playing = False
        json_files.current_music = None
        if not self.music_queue.empty():
            await self.play_next_song(ctx)
        else:
            await vc.disconnect()
            await self.reset_queues()

    async def reset_queues(self):
        while not self.music_queue.empty():
            await self.music_queue.get()
        json_files.current_music = None

    async def get_voice_client(self, guild, channel_id):
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

class MusicControlView(discord.ui.View):
    def __init__(self, cog:MusicCog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="⏯️", style=discord.ButtonStyle.primary)
    async def play_pause(self, interaction:discord.Interaction, button:discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        vc = discord.utils.get(self.cog.bot.voice_clients, guild=interaction.guild)
        if vc and vc.is_playing():
            vc.pause()
            json_files.is_music_playing = False
        elif vc:
            vc.resume()
            json_files.is_music_playing = True

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.primary)
    async def skip(self, interaction:discord.Interaction, button:discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        vc = discord.utils.get(self.cog.bot.voice_clients, guild=interaction.guild)
        if vc:
            vc.stop()
            json_files.is_music_playing = False

    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.primary)
    async def stop(self, interaction:discord.Interaction, button:discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        vc = discord.utils.get(self.cog.bot.voice_clients, guild=interaction.guild)
        if vc:
            vc.stop()
            await vc.disconnect()
            json_files.is_music_playing = False
            await self.cog.reset_queues()

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(MusicCog(bot))