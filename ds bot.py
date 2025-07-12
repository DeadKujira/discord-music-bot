import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio

# Настройки бота
TOKEN = "TOKEN"
PREFIX = "!"

# Настройки для yt-dlp (чтобы избежать ошибок)
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Настройка интентов
intents = discord.Intents.default()
intents.message_content = True  # Для чтения содержимого сообщений
intents.members = True          # Для работы с участниками сервера

# Создание бота
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"Бот {bot.user.name} готов к работе!")

@bot.command(name="play", help="Воспроизводит музыку с YouTube")
async def play(ctx, url):
    if not ctx.author.voice:
        await ctx.send("Вы не в голосовом канале!")
        return
    
    channel = ctx.author.voice.channel
    
    try:
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            if not ctx.voice_client:
                await channel.connect()
            ctx.voice_client.play(player, after=lambda e: print(f"Ошибка: {e}") if e else None)
        
        await ctx.send(f"Сейчас играет: **{player.title}**")
    except Exception as e:
        await ctx.send(f"Ошибка: {e}")

@bot.command(name="stop", help="Останавливает музыку")
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Бот отключен.")
    else:
        await ctx.send("Бот не в голосовом канале!")

@bot.command(name="pause", help="Приостанавливает музыку")
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Музыка приостановлена.")
    else:
        await ctx.send("Сейчас ничего не играет.")

@bot.command(name="resume", help="Продолжает воспроизведение")
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Музыка продолжена.")
    else:
        await ctx.send("Музыка не была на паузе.")

bot.run(TOKEN)