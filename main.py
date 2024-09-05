import sys
import subprocess
import os

try: # discord
    from discord.ext import commands
    from discord import Game, Status, Intents
except:
    subprocess.check_call([sys.executable,'-m', 'pip', 'install', '--upgrade', 'discord'])
    subprocess.check_call([sys.executable,'-m', 'pip', 'install', '--upgrade', 'discord.py'])
    from discord.ext import commands
    from discord import Game, Status, Intents

from files.log import setup_logging, handle_exception
import configparser

class main(commands.Bot):
    def __init__(self, app_id):

        self.logger = setup_logging()
        sys.excepthook = handle_exception

        current_script_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(current_script_path)

        super().__init__(
            command_prefix='',
            intents=Intents.all(),
            sync_all_commands=True,
            application_id=app_id
        )
        self.initial_extension = [
            "files.Cogs.permissions",
            "files.Cogs.temporary_channels",
            "files.Cogs.tickets",
            "files.Cogs.entry_exit_channels",
            "files.Cogs.log",
            "files.Cogs.levels",
            "files.Cogs.roles",
            "files.Cogs.Cogs_tts",
            "files.Cogs.Cogs_music",
            "files.Cogs.Cogs_game"
        ]
        self.remove_command("help")

    async def setup_hook(self):
        for ext in self.initial_extension:
            await self.load_extension(ext)
        await self.tree.sync()

    async def on_ready(self):
        print("login")
        print(self.user.name)
        print(self.user.id)
        print("===============")
        game = Game("서버 관리")
        await self.change_presence(status=Status.online, activity=game)  


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')
    app_id = config['Settings']['applications_id']
    token = config['Settings']['token']

    bot = main(app_id)
    bot.run(f'{token}')
