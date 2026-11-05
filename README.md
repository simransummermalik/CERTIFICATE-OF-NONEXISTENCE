# Certificate of Nonexistence

### No. 1 Holonomy Lane

---

The listing went up on a Thursday in November.

*Hilbert & Co. Fine properties. Rooms without end.* No. 1 Holonomy Lane, Charlotte, North Carolina. Two bedrooms, one bath, four storeys, eighteen rooms. Price upon request.

The photographs were very good. They showed a stair hall of board-formed concrete. From the parapet on the first landing you could look straight down the well and see the flights turning beneath you, landing after landing, smaller and smaller, until the light gave out. They showed a long hall in white oak with a slot of sky along its ceiling and a dark ceramic sphere on a table at the far end. And they showed a tape measure lying along the skirting with its case pressed against the wall, as though someone had just stepped away from it.

The copy said the hall was generous by exactly one quarter of an inch. Nobody asked what that meant.

---

The inspector came the following week and did what inspectors do.

Every room in the house had been drawn on its own sheet, in its own frame. Each sheet showed where that room's walls were, where its doors were, and how high its ceiling ran. No room knew where any other room was. A room knew only its doors, and each door knew which door on the far side it met.

So the inspector went room by room. Ceiling heights: fourteen of fourteen. Door widths and heights: seventeen of seventeen. Hallway widths, stair widths, headroom, risers, treads. Every doorway matched its partner. Ninety-two checks against the residential building code, and ninety-two passed.

Then the inspector did the one thing the building code never asks for. Starting at the front door, the inspector laid the rooms down one at a time on a single sheet of paper. Each room was placed by the doorway that led into it, the way you would assemble a house if all you had were its rooms.

All eighteen rooms went down. Then three doorways would not close. Each one, when the inspector came round to it from the other side, opened onto the wrong place.

**The stair.** The stair hall has four flights. Each one climbs a storey: sixteen risers of seven and a quarter inches, nine feet eight inches in all. Each arrives on a landing, turns, and climbs again. At the top of the fourth flight is a landing with a door, a lamp, and a numeral painted on the wall: **1**. It is the landing you started from. Every flight is correct. Carry your sense of height up all four, though, and bring it home, and it says you are thirty-eight feet eight inches above the place where you are standing.

**The cloister.** Five galleries enclose a court of raked gravel with a single stone at its centre. Each gallery turns right into the next. Walk once round and you have made five right turns, four hundred and fifty degrees, where any walk around a square court should turn three hundred and sixty. The fifth gallery stands in the place of the first, a quarter turn askew. The stone, if you could ask it, sees more horizon than there is.

**The hall.** The hall runs from the library to the entrance and measures thirty-eight feet six and a quarter inches. Beside it, the dining room, a wall and the living room together measure thirty-eight feet six. The tape was right both times.

---

Mathematicians have a word for what goes wrong here: *holonomy*. You carry something around a closed loop, a direction or a height or a ruler, and see whether it comes home the same. On a flat floor it always does. In this house it fails three times. Every room is flat, but the house, taken together, is not. There is nowhere in ordinary space to put it.

The inspector did not take this on faith. The question went to a theorem prover. Here are eighteen rooms and twenty-two doorways: give each room a position and a heading so that every door meets its partner exactly. In under a fifth of a second the prover answered with one word, **unsat**, and a proof one hundred and ninety-six lines long. It named the smallest contradiction it could find: the four flights of the stair.

It also found the cure. Brick up one stair door, one cloister door and one hall door, and the house can exist. That works for sixty-four of the 1,540 ways of closing three doorways. Close only one or two, and it still cannot.

---

Nobody bricked up a door. The house was built anyway.

It can only be built one way: room by room, through every doorway, putting each room exactly where its door says it must go. Go once round the cloister and the whole house must stand again, turned a quarter turn about the stone. Go round again, and again: four houses at once, sharing one courtyard and one stone, their walls running straight through each other's rooms. Climb the stair and all four must stand again, thirty-eight feet eight inches higher. Then again. It does not stop.

**The House, Built Anyway** is that building, drawn in ink from above the way an architect draws a plan. The top storey is cut open at five feet so you can see into every room, its cut walls filled black. Every room is furnished, four times over: four dining tables, four grand pianos, twelve beds, each turned a quarter turn from the last, standing in one another's walls. Below, the tower falls away, storey after storey of the same four houses, until the lines grow too faint to draw. Every wall is where the proof says it has to be.

At the centre is the court, the one place all four houses agree on. Its gravel is raked in rings around the stone and in squares out to the colonnade, the only patterns a quarter turn leaves unchanged. A man in an overcoat and a bowler hat stands beside the stone. His footprints cross the gravel from the colonnade. He is the only one there.

The photographs are from inside. **Looking down** the stair hall from the first landing, the flights turn beneath you, landing after landing, smaller and smaller, until the light gives out. **Looking up**, they turn above you the same way. **The hall** runs east under its slot of sky, a quarter of an inch longer than the rooms beside it, which no photograph can show. The rooms were built to the same quarter-inch dimensions the inspector checked, and lit by simulated sunlight. Nothing was painted in to make the impossible look plausible.

*The property has passed every inspection except existence.*

---

## Inspect it yourself

You don't have to trust the inspector. Run

```
python3 verify.py
```

It uses whole numbers and Python's standard library, nothing else. It rereads the house, carries a frame of reference through the doorways around each loop, and reports what comes home:

```
3 loop(s) fail to close. The building cannot exist in Euclidean space.
```

---

The images are in `submission/`. How the house, the proof and the pictures are made is in [BUILD.md](BUILD.md).
