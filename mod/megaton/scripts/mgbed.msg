# mgbed.msg - beds the player may rest in (mgbed.ssl).
# 100-109 look and examine, 110-119 refusals, 200+ the rest menu.
# One entry per line; no braces in comment lines.

{100}{}{You see a bed.}
# Examine: 101 a bed in the Common House, 102 the player's own bed, 103 the house bed before the house is his.
{101}{}{A mattress and a blanket that has outlived several owners. In the Common House nobody asks whose it is.}
{102}{}{Your bed. It sags in the middle, like the town.}
{103}{}{A narrow bed in a house that is not yours.}
# 104 is added to 101 or 102 when the player examines the bed from too far away.
{104}{}{ You would have to stand beside it to lie down.}

{110}{}{This is not your bed, and in a town this small the sheriff would hear of it by noon.}
{111}{}{This is no time for a nap.}
{112}{}{With the whole town hunting you, it would be a short sleep.}

{200}{}{A bed in the Common House. The blanket is thin and the roof mostly holds, and nobody will charge you for either.}
{201}{}{Your own bed, in your own house. The mattress has a dip in it the shape of somebody else, but the door locks.}
{210}{}{[Rest until you are healed.]}
{211}{}{[Sleep for eight hours.]}
{212}{}{[Sleep until morning.]}
{213}{}{[Leave it.]}
{214}{}{[Get up.]}

# The result is built as 220 + hours + 221, or 222 for a single hour, plus 224 (fully healed) or 225 (better).
{220}{}{You sleep for }
{221}{}{ hours. Nothing wakes you, which around here counts as luxury.}
{222}{}{You doze for an hour. Nothing wakes you, which around here counts as luxury.}
{224}{}{ You feel whole again.}
{225}{}{ You feel somewhat better.}
