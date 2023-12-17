

from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
import logging
from collections import defaultdict
from colorsys import rgb_to_hsv
from typing import List, Optional

import discord
from grief.core import commands
from grief import Grief
from grief.core.utils.chat_formatting import humanize_number as hn
from grief.core.utils.chat_formatting import pagify, text_to_file
from grief.core.utils.mod import get_audit_reason
from TagScriptEngine import Interpreter, LooseVariableGetterBlock, MemberAdapter

from .abc import MixinMeta
from .converters import FuzzyRole, StrictRole, TargeterArgs, TouchableMember
from .utils import (
    can_run_command,
    guild_roughly_chunked,
    humanize_roles,
    is_allowed_by_role_hierarchy,
)

import aiohttp
import typing
import emoji

from grief.core.utils.chat_formatting import box, pagify

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0


log = logging.getLogger("grief.roleutils")

_ = lambda s: s



GENERIC_FORBIDDEN = _(
    "I attempted to do something that Discord denied me permissions for."
    " Your command failed to successfully complete."
)

HIERARCHY_ISSUE_ADD = _(
    "I can not give {role.name} to {member.display_name}"
    " because that role is higher than or equal to my highest role"
    " in the Discord hierarchy."
)

HIERARCHY_ISSUE_REMOVE = _(
    "I can not remove {role.name} from {member.display_name}"
    " because that role is higher than or equal to my highest role"
    " in the Discord hierarchy."
)

ROLE_HIERARCHY_ISSUE = _(
    "I can not edit {role.name}"
    " because that role is higher than my or equal to highest role"
    " in the Discord hierarchy."
)

USER_HIERARCHY_ISSUE_ADD = _(
    "I can not let you give {role.name} to {member.display_name}"
    " because that role is higher than or equal to your highest role"
    " in the Discord hierarchy."
)

USER_HIERARCHY_ISSUE_REMOVE = _(
    "I can not let you remove {role.name} from {member.display_name}"
    " because that role is higher than or equal to your highest role"
    " in the Discord hierarchy."
)

ROLE_USER_HIERARCHY_ISSUE = _(
    "I can not let you edit {role.name}"
    " because that role is higher than or equal to your highest role"
    " in the Discord hierarchy."
)

NEED_MANAGE_ROLES = _('I need the "Manage Roles" permission to do that.')

RUNNING_ANNOUNCEMENT = _(
    "I am already announcing something. If you would like to make a"
    " different announcement please use `{prefix}announce cancel`"
    " first."
)

ERROR_MESSAGE = _("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}")

def targeter_cog(ctx: commands.Context):
    cog = ctx.bot.get_cog("Targeter")
    return cog is not None and hasattr(cog, "args_to_list")


def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    https://github.com/flaree/flare-cogs/blob/08b78e33ab814aa4da5422d81a5037ae3df51d4e/commandstats/commandstats.py#L16
    """
    for i in range(0, len(l), n):
        yield l[i : i + n]

class RoleUtils(commands.Cog):
        """RoleUtils for your community."""

class EmojiOrUrlConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        try:
            return await discord.ext.commands.converter.CONVERTER_MAPPING[discord.Emoji]().convert(
                ctx, argument
            )
        except commands.BadArgument:
            pass
        if argument.startswith("<") and argument.endswith(">"):
            argument = argument[1:-1]
        return argument


class PositionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            position = int(argument)
        except ValueError:
            raise commands.BadArgument(_("The position must be an integer."))
        max_guild_roles_position = len(ctx.guild.roles)
        if position <= 0 or position >= max_guild_roles_position + 1:
            raise commands.BadArgument(
                _(
                    "The indicated position must be between 1 and {max_guild_roles_position}."
                ).format(max_guild_roles_position=max_guild_roles_position)
            )
        _list = list(range(max_guild_roles_position - 1))
        _list.reverse()
        position = _list[position - 1]
        return position + 1


class PermissionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        permissions = [
            key for key, value in dict(discord.Permissions.all_channel()).items() if value
        ]
        if argument not in permissions:
            raise commands.BadArgument(_("This permission is invalid."))
        return argument

class Roles(MixinMeta):
    """
    Useful role commands.
    """

    def __init__(self):
        self.interpreter = Interpreter([LooseVariableGetterBlock()])
        super().__init__()

    async def initialize(self):
        log.debug("Roles Initialize")
        await super().initialize()

    async def check_role(self, ctx: commands.Context, role: discord.Role) -> bool:
        if (
            not ctx.author.top_role > role
            and ctx.author.id != ctx.guild.owner.id
            and ctx.author.id not in ctx.bot.owner_ids
        ):
            raise commands.UserFeedbackCheckFailure(
                (
                    "I can not let you edit @{role.name} ({role.id}) because that role is higher than or equal to your highest role in the Discord hierarchy."
                ).format(role=role),
            )
        if not ctx.me.top_role > role:
            raise commands.UserFeedbackCheckFailure(
                (
                    "I can not edit @{role.name} ({role.id}) because that role is higher than or equal to my highest role in the Discord hierarchy."
                ).format(role=role),
            )
        return True

    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True)
    async def role(
        self, ctx: commands.Context, member: TouchableMember(False), *, role: StrictRole(False)
    ):
        """Base command for modifying roles.
        """
        if role in member.roles and await can_run_command(ctx, "role remove"):
            com = self.bot.get_command("role remove")
            await ctx.invoke(
                com,
                member=member,
                role=role,
            )
        elif role not in member.roles and await can_run_command(ctx, "role add"):
            com = self.bot.get_command("role add")
            await ctx.invoke(
                com,
                member=member,
                role=role,
            )
        else:
            await ctx.send_help()

    def format_member(self, member: discord.Member, formatting: str) -> str:
        output = self.interpreter.process(formatting, {"member": MemberAdapter(member)})
        return output.body

    @commands.has_guild_permissions(manage_roles=True)
    @role.command("create")
    async def role_create(
        self,
        ctx: commands.Context,
        color: Optional[discord.Color] = discord.Color.default(),
        hoist: Optional[bool] = False,
        *,
        name: str = None,
    ):
        """
        Creates a role.
        """
        if len(ctx.guild.roles) >= 250:
            return await ctx.reply("This server has reached the maximum role limit (250).", mention_author=False)

        role = await ctx.guild.create_role(name=name, colour=color, hoist=hoist)
        await ctx.tick()

    @commands.has_guild_permissions(manage_roles=True)
    @role.command("color", aliases=["colour"])
    async def role_color(
        self, ctx: commands.Context, role: StrictRole(check_integrated=False), color: discord.Color
    ):
        """Edit a role's color."""
        await role.edit(color=color)
        await ctx.tick()

    @commands.has_guild_permissions(manage_roles=True)
    @role.command("hoist")
    async def role_hoist(
        self,
        ctx: commands.Context,
        role: StrictRole(check_integrated=False),
        hoisted: bool = None,
    ):
        """Edit role hoist."""
        hoisted = hoisted if hoisted is not None else not role.hoist
        await role.edit(hoist=hoisted)
        now = "now" if hoisted else "no longer"
        await ctx.reply(f"**{role}** is {now} hoisted.", mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @role.command("name")
    async def role_name(
        self, ctx: commands.Context, role: StrictRole(check_integrated=False), *, name: str
    ):
        """Change a role's name."""
        await role.edit(name=name)
        await ctx.tick()

    @commands.has_guild_permissions(manage_roles=True)
    @role.command("add")
    async def role_add(self, ctx: commands.Context, member: TouchableMember, *, role: StrictRole):
        """Add a role to a member."""
        if role in member.roles:
            await ctx.reply(
                f"**{member}** already has the role **{role}**. Maybe try removing it instead.", mention_author=False)
            return
        reason = get_audit_reason(ctx.author)
        await member.add_roles(role, reason=reason)
        await ctx.tick()

    @commands.has_guild_permissions(manage_roles=True)
    @role.command("remove")
    async def role_remove(
        self, ctx: commands.Context, member: TouchableMember, *, role: StrictRole
    ):
        """Remove a role from a member."""
        if role not in member.roles:
            await ctx.reply(f"**{member}** doesn't have the role **{role}**. Maybe try adding it instead.", mention_author=False)
            return
        reason = get_audit_reason(ctx.author)
        await member.remove_roles(role, reason=reason)
        await ctx.tick()

    @commands.has_guild_permissions(manage_roles=True)
    @role.command(require_var_positional=True)
    async def addmulti(self, ctx: commands.Context, role: StrictRole, *members: TouchableMember):
        """Add a role to multiple members."""
        reason = get_audit_reason(ctx.author)
        already_members = []
        success_members = []
        for member in members:
            if role not in member.roles:
                await member.add_roles(role, reason=reason)
                success_members.append(member)
            else:
                already_members.append(member)
        msg = []
        if success_members:
            msg.append(f"Added **{role}** to {humanize_roles(success_members)}.")
        if already_members:
            msg.append(f"{humanize_roles(already_members)} already had **{role}**.")
        await ctx.send("\n".join(msg))

    @commands.has_guild_permissions(manage_roles=True)
    @role.command(require_var_positional=True)
    async def removemulti(
        self, ctx: commands.Context, role: StrictRole, *members: TouchableMember
    ):
        """Remove a role from multiple members."""
        reason = get_audit_reason(ctx.author)
        already_members = []
        success_members = []
        for member in members:
            if role in member.roles:
                await member.remove_roles(role, reason=reason)
                success_members.append(member)
            else:
                already_members.append(member)
        msg = []
        if success_members:
            msg.append(f"Removed **{role}** from {humanize_roles(success_members)}.")
        if already_members:
            msg.append(f"{humanize_roles(already_members)} didn't have **{role}**.")
        await ctx.send("\n".join(msg))

    @commands.has_guild_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True, require_var_positional=True)
    async def multirole(self, ctx: commands.Context, member: TouchableMember, *roles: StrictRole):
        """Add multiple roles to a member."""
        not_allowed = []
        already_added = []
        to_add = []
        for role in roles:
            allowed = await is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
            if not allowed[0]:
                not_allowed.append(role)
            elif role in member.roles:
                already_added.append(role)
            else:
                to_add.append(role)
        reason = get_audit_reason(ctx.author)
        msg = []
        if to_add:
            await member.add_roles(*to_add, reason=reason)
            msg.append(f"Added {humanize_roles(to_add)} to **{member}**.")
        if already_added:
            msg.append(f"**{member}** already had {humanize_roles(already_added)}.")
        if not_allowed:
            msg.append(f"You do not have permission to assign the roles {humanize_roles(not_allowed)}.")
        await ctx.reply("\n".join(msg), mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @multirole.command("remove", require_var_positional=True)
    async def multirole_remove(
        self, ctx: commands.Context, member: TouchableMember, *roles: StrictRole
    ):
        """Remove multiple roles from a member."""
        not_allowed = []
        not_added = []
        to_rm = []
        for role in roles:
            allowed = await is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
            if not allowed[0]:
                not_allowed.append(role)
            elif role not in member.roles:
                not_added.append(role)
            else:
                to_rm.append(role)
        reason = get_audit_reason(ctx.author)
        msg = []
        if to_rm:
            await member.remove_roles(*to_rm, reason=reason)
            msg.append(f"Removed {humanize_roles(to_rm)} from **{member}**.")
        if not_added:
            msg.append(f"**{member}** didn't have {humanize_roles(not_added)}.")
        if not_allowed:
            msg.append(f"You do not have permission to assign the roles {humanize_roles(not_allowed)}.")
        await ctx.reply("\n".join(msg), mention_author=False)

    @commands.has_guild_permissions(manage_roles=True)
    @role.command()
    async def all(self, ctx: commands.Context, *, role: StrictRole):
        """Add a role to all members of the server."""
        await self.super_massrole(ctx, ctx.guild.members, role)

    @commands.has_guild_permissions(manage_roles=True)
    @role.command(aliases=["removeall"])
    async def rall(self, ctx: commands.Context, *, role: StrictRole):
        """Remove a role from all members of the server."""
        member_list = self.get_member_list(ctx.guild.members, role, False)
        await self.super_massrole(ctx, member_list, role, "No one on the server has this role.", False)

    @commands.has_guild_permissions(manage_roles=True)
    @role.command()
    async def humans(self, ctx: commands.Context, *, role: StrictRole):
        """Add a role to all humans."""
        await self.super_massrole(ctx,[member for member in ctx.guild.members if not member.bot], role, "Every human in the server has this role.",)

    @commands.has_guild_permissions(manage_roles=True)
    @role.command()
    async def rhumans(self, ctx: commands.Context, *, role: StrictRole):
        """Remove a role from all humans."""
        await self.super_massrole( ctx, [member for member in ctx.guild.members if not member.bot], role, "None of the humans in the server have this role.", False,)

    @commands.has_guild_permissions(manage_roles=True)
    @role.command()
    async def bots(self, ctx: commands.Context, *, role: StrictRole):
        """Add a role to all bots."""
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if member.bot],
            role,
            "Every bot in the server has this role.",
        )

    @commands.has_guild_permissions(manage_roles=True)
    @role.command()
    async def rbots(self, ctx: commands.Context, *, role: StrictRole):
        """Remove a role from all bots."""
        await self.super_massrole(ctx, [member for member in ctx.guild.members if member.bot], role, "None of the bots in the server have this role.", False,)

    @commands.has_guild_permissions(manage_roles=True)
    @role.command("in")
    async def role_in(
        self, ctx: commands.Context, target_role: FuzzyRole, *, add_role: StrictRole
    ):
        """Add a role to all members of a another role."""
        await self.super_massrole(
            ctx,
            [member for member in target_role.members],
            add_role,
            f"Every member of **{target_role}** has this role.",
        )

    @commands.has_guild_permissions(manage_roles=True)
    @role.command("rin")
    async def role_rin(
        self, ctx: commands.Context, target_role: FuzzyRole, *, remove_role: StrictRole
    ):
        """Remove a role from all members of a another role."""
        await self.super_massrole(
            ctx,
            [member for member in target_role.members],
            remove_role,
            f"No one in **{target_role}** has this role.",
            False,
        )

    @commands.check(targeter_cog)
    @commands.has_guild_permissions(manage_roles=True)
    @role.group()
    async def target(self, ctx: commands.Context):
        """
        Modify roles using 'targeting' args.
        """

    @target.command("add")
    async def target_add(self, ctx: commands.Context, role: StrictRole, *, args: TargeterArgs):
        """
        Add a role to members.
        """
        await self.super_massrole(
            ctx,
            args,
            role,
            f"No one was found with the given args that was eligible to recieve **{role}**.",
        )

    @target.command("remove")
    async def target_remove(self, ctx: commands.Context, role: StrictRole, *, args: TargeterArgs):
        """
        Remove a role from members.
        """
        await self.super_massrole(
            ctx,
            args,
            role,
            f"No one was found with the given args that was eligible have **{role}** removed from them.",
            False,
        )

    async def super_massrole(
        self,
        ctx: commands.Context,
        members: list,
        role: discord.Role,
        fail_message: str = "Everyone in the server has this role.",
        adding: bool = True,
    ):
        if guild_roughly_chunked(ctx.guild) is False and self.bot.intents.members:
            await ctx.guild.chunk()
        member_list = self.get_member_list(members, role, adding)
        if not member_list:
            await ctx.send(fail_message)
            return
        verb = "add" if adding else "remove"
        word = "to" if adding else "from"
        await ctx.send(
            f"Beginning to {verb} **{role.name}** {word} **{len(member_list)}** members."
        )
        async with ctx.typing():
            result = await self.massrole(member_list, [role], get_audit_reason(ctx.author), adding)
            result_text = f"{verb.title()[:5]}ed **{role.name}** {word} **{len(result['completed'])}** members."
            if result["skipped"]:
                result_text += (
                    f"\nSkipped {verb[:5]}ing roles for **{len(result['skipped'])}** members."
                )
            if result["failed"]:
                result_text += (
                    f"\nFailed {verb[:5]}ing roles for **{len(result['failed'])}** members."
                )
        await ctx.send(result_text)

    def get_member_list(self, members: list, role: discord.Role, adding: bool = True):
        if adding:
            members = [member for member in members if role not in member.roles]
        else:
            members = [member for member in members if role in member.roles]
        return members

    async def massrole(self, members: list, roles: list, reason: str, adding: bool = True):
        completed = []
        skipped = []
        failed = []
        for member in members:
            if adding:
                to_add = [role for role in roles if role not in member.roles]
                if to_add:
                    try:
                        await member.add_roles(*to_add, reason=reason)
                    except Exception as e:
                        failed.append(member)
                        log.exception(f"Failed to add roles to {member}", exc_info=e)
                    else:
                        completed.append(member)
                else:
                    skipped.append(member)
            else:
                to_remove = [role for role in roles if role in member.roles]
                if to_remove:
                    try:
                        await member.remove_roles(*to_remove, reason=reason)
                    except Exception as e:
                        failed.append(member)
                        log.exception(f"Failed to remove roles from {member}", exc_info=e)
                    else:
                        completed.append(member)
                else:
                    skipped.append(member)
        return {"completed": completed, "skipped": skipped, "failed": failed}

    @staticmethod
    def format_members(members: List[discord.Member]):
        length = len(members)
        s = "" if length == 1 else "s"
        return f"**{hn(length)}** member{s}"

    @role.command("uniquemembers", aliases=["um"], require_var_positional=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def role_uniquemembers(self, ctx: commands.Context, *roles: FuzzyRole):
        """
        View the total unique members between multiple roles.
        """
        roles_length = len(roles)
        if roles_length == 1:
            raise commands.UserFeedbackCheckFailure("You must provide at least 2 roles.")
        if not ctx.guild.chunked:
            await ctx.guild.chunk()
        color = roles[0].color
        unique_members = set()
        description = []
        for role in roles:
            unique_members.update(role.members)
            description.append(f"{role.mention}: {self.format_members(role.members)}")
        description.insert(0, f"**Unique members**: {self.format_members(unique_members)}")
        e = discord.Embed(
            color=color,
            title=f"Unique members between {roles_length} roles",
            description="\n".join(description),
        )
        ref = ctx.message.to_reference(fail_if_not_exists=False)
        await ctx.send(embed=e, reference=ref)

        
    @role.command(name="delete")
    @commands.has_guild_permissions(manage_roles=True)
    async def role_delete(
        self,
        ctx: commands.Context,
        role: discord.Role,
        confirmation: bool = False,
    ) -> None:
        """Delete a role."""
        await self.check_role(ctx, role)
        if not confirmation and not ctx.assume_yes:
            if ctx.bot_permissions.embed_links:
                embed: discord.Embed = discord.Embed()
                embed.description = (
                    "Do you really want to delete the role {role.mention}?"
                ).format(role=role)
                embed.color = 0x313338
            else:
                embed = None
                content = f"{ctx.author.mention} " + (
                    "Do you really want to delete the role {role.mention} ({role.id})?"
                ).format(role=role)
            if not await CogsUtils.ConfirmationAsk(
                ctx, embed=embed
            ):
                await CogsUtils.delete_message(ctx.message)
                return
        try:
            await role.delete(
                reason=f"{ctx.author} ({ctx.author.id}) has deleted the role {role.name} ({role.id})."
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
            
    @role.command(name="icon")
    @commands.has_guild_permissions(manage_roles=True)
    async def role_icon(
        self, ctx: commands.Context, role: discord.Role, display_icon: typing.Optional[EmojiOrUrlConverter] = None) -> None:
        """Edit role display icon.
        """
        if "ROLE_ICONS" not in ctx.guild.features:
            raise commands.UserFeedbackCheckFailure(_("This server doesn't have `ROLE_ICONS` feature. This server needs more boosts to perform this action."))
        await self.check_role(ctx, role)
        if len(ctx.message.attachments) > 0:
            display_icon = await ctx.message.attachments[0].read()  # Read an optional attachment.
        elif display_icon is not None:
            if isinstance(display_icon, discord.Emoji):
                # emoji_url = f"https://cdn.discordapp.com/emojis/{display_icon.id}.png"
                # async with aiohttp.ClientSession() as session:
                #     async with session.get(emoji_url) as r:
                #         display_icon = await r.read()  # Get emoji data.
                display_icon = await display_icon.read()
            elif display_icon.strip("\N{VARIATION SELECTOR-16}") in EMOJI_DATA:
                display_icon = display_icon
            else:
                url = display_icon
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(url) as r:
                            display_icon = await r.read()  # Get URL data.
                    except aiohttp.InvalidURL:
                        return await ctx.send("That URL is invalid.")
                    except aiohttp.ClientError:
                        return await ctx.send("Something went wrong while trying to get the image.")
        else:
            await ctx.send_help()  # Send the command help if no attachment, no Unicode/custom emoji and no URL.
            return
        try:
            await role.edit(
                display_icon=display_icon,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
            await ctx.tick()
        
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
        
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @role.command(name="list")
    async def role_list(self, ctx: commands.Context,) -> None:
        """List all roles in the current guild."""
        description = "".join(
            f"\n**•** **{len(ctx.guild.roles) - role.position}** - {role.mention} ({role.id}) - {len(role.members)} members"
            for role in sorted(ctx.guild.roles, key=lambda x: x.position, reverse=True)
        )
        embed: discord.Embed = discord.Embed(color=await ctx.embed_color())
        embed.title = _("List of roles in {guild.name} ({guild.id})").format(guild=ctx.guild)
        embeds = []
        pages = pagify(description, page_length=4096)
        for page in pages:
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @role.command(name="position")
    async def role_position(
        self, ctx: commands.Context, role: discord.Role, position: PositionConverter
    ) -> None:
        """Edit role position.

        Warning: The role with a position 1 is the highest role in the Discord hierarchy.
        """
        await self.check_role(ctx, role)
        try:
            await role.edit(
                position=position,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
            await ctx.tick()
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py")))
        

    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @role.command(name="permissions")
    async def role_permissionss(
        self, ctx: commands.Context, role: discord.Role, true_or_false: bool, permissions: commands.Greedy[PermissionConverter]
    ) -> None:
        """Edit role permissions.

        You must possess the permissions you wish to modify.

        • `create_instant_invite`
        • `manage_channels`
        • `add_reactions`
        • `priority_speaker`
        • `stream`
        • `read_messages`
        • `send_messages`
        • `send_tts_messages`
        • `manage_messages`
        • `embed_links`
        • `attach_files`
        • `read_message_history`
        • `mention_everyone`
        • `external_emojis`
        • `connect`
        • `speak`
        • `mute_members`
        • `deafen_members`
        • `move_members`
        • `use_voice_activation`
        • `manage_roles`
        • `manage_webhooks`
        • `use_application_commands`
        • `request_to_speak`
        • `manage_threads`
        • `create_public_threads`
        • `create_private_threads`
        • `external_stickers`
        • `send_messages_in_threads`
        """
        await self.check_role(ctx, role)
        if not permissions:
            raise commands.UserFeedbackCheckFailure(
                _("You need to provide at least one permission.")
            )
        role_permissions = role.permissions
        for permission in permissions:
            if not getattr(ctx.author.guild_permissions, permission):
                raise commands.UserFeedbackCheckFailure(_("You don't have the permission {permission_name} in this guild.").format(permission_name=permission))
            setattr(role_permissions, permission, true_or_false)
        try:
            await role.edit(
                permissions=role_permissions,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
            await ctx.tick()
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
        
async def setup(bot: Grief):
    cog = RoleUtils(bot)
    await bot.add_cog, cog