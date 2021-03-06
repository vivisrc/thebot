import re
import typing

import discord
from bot import cmd, converter
from discord.ext import commands


class Emoji(cmd.Cog):
    """Emoji related commands"""

    @commands.command(aliases=["emote"])
    @commands.cooldown(3, 8, commands.BucketType.channel)
    async def emoji(self, ctx: cmd.Context, *, emoji: converter.PartialEmojiConverter):
        """Shows info about an emoji"""

        embed = discord.Embed(
            title=f"Emoji info",
            description=f"Name: `{emoji.name}`"
            f"\nID: `{emoji.id}`"
            f"\nAnimated: {'yes' if emoji.animated else 'no'}"
            f"\nMarkdown: `{str(emoji).strip('<>')}`"
            f"\nImage: {emoji.url}",
        )
        embed.set_image(url=emoji.url)

        await ctx.reply(embed=embed)

    emoji_name_re = re.compile(r"\w{2,32}")
    emoji_md_re = re.compile(r"<(a?):([a-zA-Z0-9\_]+):([0-9]+)>")

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    async def steal(
        self,
        ctx: cmd.Context,
        emoji_or_message: typing.Union[
            converter.PartialEmojiConverter, discord.Message
        ],
        *,
        name: str = None,
    ):
        """Steals an emoji from another server"""

        emoji = None
        if isinstance(emoji_or_message, (discord.Emoji, discord.PartialEmoji)):
            emoji = emoji_or_message
        else:
            matches = set(self.emoji_md_re.findall(emoji_or_message.content))
            if len(matches) > 1:
                await ctx.send(
                    embed=discord.Embed(
                        title="Ambiguous",
                        description="The message contained more than one emoji.",
                    )
                )
                return
            if len(matches) == 0:
                await ctx.send(
                    embed=discord.Embed(
                        title="Not found",
                        description="The given message did not contain an emoji.",
                    )
                )
                return

            animated, emoji_name, emoji_id = matches.pop()
            emoji = discord.PartialEmoji.with_state(
                ctx.bot._connection,
                animated=bool(animated),
                name=emoji_name,
                id=int(emoji_id),
            )

        if (
            sum(1 for e in ctx.guild.emojis if e.animated == emoji.animated)
            >= ctx.guild.emoji_limit
        ):
            emoji_type = "animated emojis" if emoji.animated else "emojis"

            await ctx.reply(
                embed=discord.Embed(
                    title="Emoji limit reached",
                    description=f"You can't add more than {ctx.guild.emoji_limit} {emoji_type}.",
                )
            )
            return

        if name and not self.emoji_name_re.fullmatch(name):
            await ctx.reply(
                embed=discord.Embed(
                    title="Emoji name invalid",
                    description=f"The emoji name can only include `a-z`, `A-Z`, `0-9`, and `_`.",
                )
            )
            return

        image_data = None

        if emoji.animated is None:
            animated = None
            asset = discord.Asset(ctx.bot._connection, f"/emojis/{emoji.id}.gif")
            try:
                image_data = await asset.read()
            except discord.HTTPException:
                animated = False

        if not image_data:
            image_data = await emoji.url.read()

        emoji = await ctx.guild.create_custom_emoji(
            name=name or emoji.name, image=image_data
        )

        await ctx.reply(
            embed=discord.Embed(
                title="Emoji stolen", description=f"Successfully added emoji {emoji}."
            )
        )

    @commands.group(invoke_without_command=True)
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    async def emojilock(self, ctx: cmd.Context):
        """Locks certain emoji to given roles only"""

        await ctx.send_help("emojilock")

    @emojilock.command(name="list")
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    async def emojilock_list(self, ctx: cmd.Context, emoji: discord.Emoji):
        """Lists which roles have access to an emoji"""

        if emoji.guild != ctx.guild:
            await ctx.reply(
                embed=discord.Embed(
                    title="Emoji role",
                    description=f"This emoji is from another server.",
                )
            )
            return

        if len(emoji.roles) > 0:
            await ctx.reply(
                embed=discord.Embed(
                    title="Emoji role",
                    description=f"{emoji} can only be used by:\n"
                    + ", ".join(map(lambda role: role.mention, emoji.roles))
                    + ".",
                )
            )
            return

        await ctx.reply(
            embed=discord.Embed(
                title="Emoji role",
                description=f"{emoji} can be used by everyone.",
            )
        )

    @emojilock.command(name="add")
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    async def emojilock_add(
        self, ctx: cmd.Context, emoji: discord.Emoji, *, role: discord.Role
    ):
        """Adds a role to be able to use an emoji"""

        if emoji.guild != ctx.guild or emoji.managed:
            await ctx.reply(
                embed=discord.Embed(
                    title="Emoji role",
                    description=f"This emoji cannot be modified or is from another server.",
                )
            )
            return

        if role in emoji.roles:
            await ctx.reply(
                embed=discord.Embed(
                    title="Emoji role",
                    description=f"{role.mention} already was able to use {emoji}.",
                )
            )
            return

        await emoji.edit(roles=[*emoji.roles, role])
        await ctx.reply(
            embed=discord.Embed(
                title="Emoji role",
                description=f"{role.mention} can now use {emoji}.",
            )
        )

    @emojilock.command(name="remove")
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    async def emojilock_remove(
        self, ctx: cmd.Context, emoji: discord.Emoji, *, role: discord.Role
    ):
        """Removes a role from being able to use an emoji"""

        if emoji.guild != ctx.guild or emoji.managed:
            await ctx.reply(
                embed=discord.Embed(
                    title="Emoji role",
                    description=f"This emoji cannot be modified or is from another server.",
                )
            )
            return

        if role not in emoji.roles:
            await ctx.reply(
                embed=discord.Embed(
                    title="Emoji role",
                    description=f"{role.mention} already was unable to use {emoji}.",
                )
            )
            return

        await emoji.edit(roles=[r for r in emoji.roles if r != role])
        await ctx.reply(
            embed=discord.Embed(
                title="Emoji role",
                description=f"{role.mention} can no longer use {emoji}.",
            )
        )

    @emojilock.command(name="clear")
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    async def emojilock_clear(self, ctx: cmd.Context, *, emoji: discord.Emoji):
        """Give everyone access to use an emoji"""

        if emoji.guild != ctx.guild or emoji.managed:
            await ctx.reply(
                embed=discord.Embed(
                    title="Emoji role",
                    description=f"This emoji cannot be modified or is from another server.",
                )
            )
            return

        await emoji.edit(roles=[])
        await ctx.reply(
            embed=discord.Embed(
                title="Emoji role",
                description=f"Cleared role list for {emoji}.",
            )
        )


def setup(bot: commands.Bot):
    voice = Emoji(bot)
    bot.add_cog(voice)
