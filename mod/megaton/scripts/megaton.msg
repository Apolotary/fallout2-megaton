# megaton.msg - text of the map script megaton.ssl, and the lines megaton.h shares
# between all Megaton scripts (ids 900 to 999: never renumber, other scripts read
# them through the MG_MSG_ constants). One entry per line; no braces in comments.

# 100: first time on the map. 101: follows it when the game began at the gate.
{100}{}{Megaton. Somebody walled a crater with pieces of a dead airplane and called it home. The elders' maps mark this place with a skull and nothing else. The wind smells of rust, brahmin and something faintly electric.}
{101}{}{You check what Arroyo sent you out with: the Vault suit, the Pip-Boy, a leather jacket, a knife, two stimpaks and a handful of coins. It is not much, but nobody has taken it from you yet.}

# 102: the town's grudge has lapsed (first entry a week or more after it turned hostile).
{102}{}{Nobody shoots at you. Megaton has a short memory, or has decided you are not worth the ammunition. People still cross the track to avoid you.}

# 110: Burke's hired guns are waiting by the caravan camp.
{110}{}{Three strangers get up from the caravan's fire, off to your right. They are not here for the water, and they have already seen you. The road out is right behind you.}

# 120: the bomb is dead and neither Simms nor his son is left to pay for it.
{120}{}{The bomb is dead, and there is nobody left in Megaton whose place it is to thank you. You decide the quiet is payment enough.}

# 130: the map was entered after the detonation (it should not be possible).
{130}{}{There is nothing here but a bowl of hot glass and a wind that has not made up its mind. You do not stay.}

# 140, 141: the saloon confrontation was settled while the player was away.
{140}{}{The town is quiet in the wrong way. While you were gone, Sheriff Simms went up to Moriarty's to arrest a man in a suit, and only the suit walked out.}
{141}{}{The town is buzzing. While you were gone, the sheriff went up to Moriarty's to arrest a man in a suit. The suit reached for something. The sheriff was quicker.}

# 900, 901: wrapped around a number by mg_give_xp.
{900}{}{You gain }
{901}{}{ experience points.}

# 902 to 904: wrapped around a number by mg_add_karma.
{902}{}{You gain }
{903}{}{You lose }
{904}{}{ karma.}

# 910 to 914: a townsperson who has just caught the player's hand in a pocket (mg_townsperson_pickup).
{910}{}{Hands where I can see them.}
{911}{}{That was mine. It is still mine. Keep it that way.}
{912}{}{Try that again and you leave town over the wall.}
{913}{}{I felt that. I'm poor, not numb.}
{914}{}{We'd hang thieves here if rope were cheaper.}

# 920 to 924: shouted by a hostile townsperson instead of talking (mg_hostile_bark).
{920}{}{Sheriff! Over here!}
{921}{}{You picked the wrong crater!}
{922}{}{Get out of our town!}
{923}{}{Somebody shoot this lunatic!}
{924}{}{Murderer!}

# 930 to 934: a hostile town's warning, shouted before anybody shoots (mg_townsperson_critter).
{930}{}{Out! Out of the gate, while you can still walk!}
{931}{}{You've got as long as it takes me to aim!}
{932}{}{Run, you fool! They won't call twice!}
{933}{}{Back off! Hands empty, and keep going!}
{934}{}{Gate's that way! Use it!}
