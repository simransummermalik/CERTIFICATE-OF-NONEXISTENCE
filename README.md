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

So there are three documents.

**I. The Property.** The listing. Every photograph in it is honest. The rooms were built in a renderer to the same quarter-inch dimensions the inspector checked, and lit by simulated sunlight. Nothing was painted in to make the impossible look plausible. The stair hall in the large photograph is built lap upon lap, two hundred storeys deep, because that is what the stair is. It does not end. It only returns.

**II. The Floor Plan.** The architect's sheet, A-101. The rooms are drawn in place, room by room, from the front door, and the three doorways that refuse to close are clouded in red. The stair is unfolded into one long section, where Level 1 at +38′-8″ is the same landing as Level 1 at 0′-0″. A detail shows the defect at full size: printed at eighteen by twenty-four inches, the red band on the drawn tape is exactly a quarter of an inch wide.

**III. The Certificate.** It is issued by the Bureau of Euclidean Inspection, Division of Existence, Form N-1, and dated the fifth of November, 2026. It lists every inspection the house passed and the one it failed. It writes out the three walks as matrices that should be the identity and are not. The proof runs around its border in microtext, twice. The inspector's signature is the prover's answer. The architect's line is left blank, waiting for a hand. Across it, slightly crooked, is a red stamp: DOES NOT EXIST.

The listing number and the certificate's serial are the same: the first digits of the house's fingerprint, `21A4 9C12 B72B C4EE`.

*The property has passed every inspection except existence.*

---

## Inspect it yourself

You don't have to trust the certificate. Run

```
python3 verify.py
```

It uses whole numbers and Python's standard library, nothing else. It rereads the house, carries a frame of reference through the doorways around each loop, and reports what comes home:

```
3 loop(s) fail to close. The building cannot exist in Euclidean space.
```

---

The plates are in `submission/`. How the house, the proof and the pictures are built is in [BUILD.md](BUILD.md).
