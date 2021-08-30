import discord
from discord import channel
from discord import client
from discord import guild
from discord import player
from discord.ext import commands
from discord import FFmpegPCMAudio
from async_timeout import timeout
from functools import partial
import random
import asyncio
import itertools
import sys
import traceback
import youtube_dl
import os
from youtube_dl import YoutubeDL

queues = {}

spotify_api = 'https://api.spotify.com/v1/tracks/{songid}'

def check_queue(ctx, id):
    if queues[id] !=[]:
        source = queues[id].pop(0)
        ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
# @bot.command(pass_context = True)
# async def leave(ctx):
#     if (ctx.voice_client):
#         await ctx.guild.voice_client.disconnect()
#         await ctx.send("Bye drink water c:")
#     else:
#         await ctx.send("I am not in a voice channel :c")

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
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
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
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #region DownloadMethods
        # @commands.command()
        # async def join(self, ctx, *, channel: discord.VoiceChannel):
        #     """Joins a voice channel"""

        #     if ctx.voice_client is not None:
        #         return await ctx.voice_client.move_to(channel)

        #     await channel.connect()

        # @commands.command()
        # async def play(self, ctx, *, query):
        #     """Plays a file from the local filesystem"""

        #     source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        #     ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

        #     await ctx.send(f'Now playing: {query}')

        # @commands.command()
        # async def yt(self, ctx, *, url):
        #     """Plays from a url (almost anything youtube_dl supports)"""

        #     async with ctx.typing():
        #         player = await YTDLSource.from_url(url, loop=self.bot.loop)
        #         ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

        #     await ctx.send(f'Now playing: {player.title}')
    #endregion
    
    @commands.command()
    async def queue(self, ctx, *, url):
        guild_id = ctx.message.guild.id
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)

            if guild_id in queues:
                queues[guild_id].append(player)
            else:
                queues[guild_id]=[player]
            await ctx.send('Added to queue')

            # check_queue(ctx,ctx.message.guild.id)
    
    @commands.command()
    async def play(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else check_queue(ctx,ctx.message.guild.id))
        
        embed = discord.Embed(title=player.title,url=player.url,description=f'Now playing: {player.title}')
        await ctx.send(embed=embed)



    # @commands.command(name='np', aliases=['song', 'current', 'currentsong', 'playing'], description="shows the current playing song")
    # async def now_playing_(self, ctx):
    #     """Display information about the currently playing song."""
    #     vc = ctx.voice_client

    #     if not vc or not vc.is_connected():
    #         embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
    #         return await ctx.send(embed=embed)

    #     player = self.get_player(ctx)
    #     if not player.current:
    #         embed = discord.Embed(title="", description="I am currently not playing anything", color=discord.Color.green())
    #         return await ctx.send(embed=embed)
        
    #     seconds = vc.source.duration % (24 * 3600) 
    #     hour = seconds // 3600
    #     seconds %= 3600
    #     minutes = seconds // 60
    #     seconds %= 60
    #     if hour > 0:
    #         duration = "%dh %02dm %02ds" % (hour, minutes, seconds)
    #     else:
    #         duration = "%02dm %02ds" % (minutes, seconds)

    #     embed = discord.Embed(title="", description=f"[{vc.source.title}]({vc.source.web_url}) [{vc.source.requester.mention}] | `{duration}`", color=discord.Color.green())
    #     embed.set_author(icon_url=self.bot.user.avatar_url, name=f"Now Playing 🎶")
    #     await ctx.send(embed=embed)

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def leave(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()

    @commands.command()
    async def pause(self,ctx):
        voice = discord.utils.get(ctx.bot.voice_clients,guild=ctx.guild)
        if voice.is_playing():
            voice.pause()
        else:
            await ctx.send("No me encuentro reproduciendo ninguna cancion")

    @commands.command()
    async def resume(self,ctx):
        voice = discord.utils.get(ctx.bot.voice_clients,guild=ctx.guild)
        if voice.is_paused():
            voice.resume()
        else:
            await ctx.send("Me encuentro reproduciendo ninguna cancion")
    
    @commands.command()
    async def stop(self,ctx):
        voice = discord.utils.get(ctx.bot.voice_clients,guild=ctx.guild)
        voice.stop()

    # @play.before_invoke
    # @yt.before_invoke
    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()




bot = commands.Bot(command_prefix=commands.when_mentioned_or("?"),
                   description='A slimy bot')


@bot.command()
async def boni(ctx):
    message = await ctx.send('Hi there <3')
    

@bot.command()
async def rommel(ctx):
    message = await ctx.send('wat ta fak')

@bot.command(pass_context = True)
async def join(ctx):
    if (ctx.author.voice):
        channel = ctx.message.author.voice.channel
        voice = await channel.connect()
    else:
        await ctx.send("I dont wanna join >:c you are not in a voice channel join first :v")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Anime"))
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print("Slimeeeeeeeee")
    print('------')
    
bot.add_cog(Music(bot))
#bot.add_cog(Examens(bot))
bot.run('')