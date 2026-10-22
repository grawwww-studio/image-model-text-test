# Battery 3, hard prompts: results (AI reading, subjective; h4 also OCR c2)

An image passes only if every rubric item passes. Rubric: prompts/battery3.json (written before generation). Cells = passes / images (seeds 101, 102).

| Model | total | h1-count7 | h2-bind-stacks | h3-cat-dog | h4-chalkboard | h5-handshake | h6-clock345 | median warm s | peak MiB |
|---|---|---|---|---|---|---|---|---|---|
| Krea 2 Turbo (9 st) | **10/12** | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 12.7 | 21368 |
| MOSS-Image SFT (50 st) | **10/12** | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 27.9 | 19032 |
| Qwen-Image-2.1 (40 st) | **12/12** | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 18.6 | 19162 |
| FIBO 2.0-dev (30 st) | **7/12** | 0/2 | 2/2 | 2/2 | 2/2 | 0/2 | 1/2 | 81.7 | 23019 |
| Qwen-Image-2512 (50 st) | **6/12** | 0/2 | 2/2 | 2/2 | 0/2 | 2/2 | 0/2 | 119.7 | 23836 |
| FLUX 3 Image Klein (16 st) | **10/12** | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 10.6 | 24024 |

## Per image (items R1..: P/F; note = what went wrong)

### h1-count7: Exactly seven red apples in a single row on a wooden table.

Rubric: R1 exactly 7 apples are visible (not 6, not 8) | R2 every apple is red | R3 the apples form one row (single line, left to right)

- FIBO 2.0-dev (30 st) seed 101: **FAIL** [FPP] 8 apples, not 7
- FIBO 2.0-dev (30 st) seed 102: **FAIL** [FPP] 8 apples, not 7
- FLUX 3 Image Klein (16 st) seed 101: **PASS** [PPP] 7 apples in one row
- FLUX 3 Image Klein (16 st) seed 102: **PASS** [PPP] 7 apples
- Krea 2 Turbo (9 st) seed 101: **PASS** [PPP] 7 apples; 3 of them with yellow-orange patches but red dominant
- Krea 2 Turbo (9 st) seed 102: **PASS** [PPP] 7 apples, dark red with yellow-green patches on two
- MOSS-Image SFT (50 st) seed 101: **PASS** [PPP] 7 apples
- MOSS-Image SFT (50 st) seed 102: **PASS** [PPP] 7 apples
- Qwen-Image-2.1 (40 st) seed 101: **PASS** [PPP] 7 apples
- Qwen-Image-2.1 (40 st) seed 102: **PASS** [PPP] 7 apples
- Qwen-Image-2512 (50 st) seed 101: **FAIL** [FPP] 6 apples, not 7
- Qwen-Image-2512 (50 st) seed 102: **FAIL** [FPP] 6 apples, not 7

### h2-bind-stacks: Left stack: blue cube on top of a red sphere; right stack: red cube on top of a blue sphere; white table.

Rubric: R1 two separate stacks side by side (4 objects: 2 cubes, 2 spheres) | R2 left stack: BLUE cube on top of a RED sphere | R3 right stack: RED cube on top of a BLUE sphere | R4 in both stacks the cube is on top and the sphere underneath

- FIBO 2.0-dev (30 st) seed 101: **PASS** [PPPP] colours muted (maroon sphere, slate-blue cube) but bindings right
- FIBO 2.0-dev (30 st) seed 102: **PASS** [PPPP] colours muted (maroon sphere, slate-blue cube) but bindings right
- FLUX 3 Image Klein (16 st) seed 101: **PASS** [PPPP] 
- FLUX 3 Image Klein (16 st) seed 102: **PASS** [PPPP] 
- Krea 2 Turbo (9 st) seed 101: **PASS** [PPPP] 
- Krea 2 Turbo (9 st) seed 102: **PASS** [PPPP] 
- MOSS-Image SFT (50 st) seed 101: **PASS** [PPPP] 
- MOSS-Image SFT (50 st) seed 102: **PASS** [PPPP] 
- Qwen-Image-2.1 (40 st) seed 101: **PASS** [PPPP] 
- Qwen-Image-2.1 (40 st) seed 102: **PASS** [PPPP] 
- Qwen-Image-2512 (50 st) seed 101: **PASS** [PPPP] 
- Qwen-Image-2512 (50 st) seed 102: **PASS** [PPPP] 

### h3-cat-dog: A cat sitting left of a dog; only the dog wears a yellow scarf; exactly two animals.

Rubric: R1 the cat is on the left and the dog on the right (viewer's left/right) | R2 a yellow scarf is on the dog | R3 the cat wears no scarf | R4 exactly two animals (one cat, one dog), no other animals

- FIBO 2.0-dev (30 st) seed 101: **PASS** [PPPP] 
- FIBO 2.0-dev (30 st) seed 102: **PASS** [PPPP] 
- FLUX 3 Image Klein (16 st) seed 101: **PASS** [PPPP] 
- FLUX 3 Image Klein (16 st) seed 102: **PASS** [PPPP] 
- Krea 2 Turbo (9 st) seed 101: **PASS** [PPPP] 
- Krea 2 Turbo (9 st) seed 102: **PASS** [PPPP] 
- MOSS-Image SFT (50 st) seed 101: **PASS** [PPPP] 
- MOSS-Image SFT (50 st) seed 102: **PASS** [PPPP] 
- Qwen-Image-2.1 (40 st) seed 101: **PASS** [PPPP] 
- Qwen-Image-2.1 (40 st) seed 102: **PASS** [PPPP] 
- Qwen-Image-2512 (50 st) seed 101: **PASS** [PPPP] 
- Qwen-Image-2512 (50 st) seed 102: **PASS** [PPPP] 

### h4-chalkboard: A cafe chalkboard that reads FRESH BREAD DAILY 7AM-2PM.

Rubric: R1 the board text reads exactly FRESH BREAD DAILY 7AM-2PM (every word and character, incl. 7AM-2PM with the hyphen; line breaks allowed) | R2 no extra, garbled or misspelled words on the board

- FIBO 2.0-dev (30 st) seed 101: **PASS** [PP]  | OCR c2: FAIL `'FRESH\n\nBREAD\n\nDAILY\n\n7AM ODIA\n\nDRIAD\n\nDAILY\n\n7AM-2PM'`
- FIBO 2.0-dev (30 st) seed 102: **PASS** [PP]  | OCR c2: PASS `'FRESH\n\nBREAD\n\nDAILY\n\n7AM-2PM\n\nDINLAND\n\nDAILY\n\n7AM-2PM'`
- FLUX 3 Image Klein (16 st) seed 101: **PASS** [PP]  | OCR c2: PASS `'FRESH\n\nDREAD\n\nFRESH\n\nBREAD\n\nDAILY\n\n7AM-2PM\n\nLIVE\n7AM-2PM'`
- FLUX 3 Image Klein (16 st) seed 102: **PASS** [PP]  | OCR c2: PASS `'FRESH\n\nBREAD\n\nFRESH\n\nBREAD\n\nDAILY\n\n7AM-2PM\n\nDAME\n7AM-2PM'`
- Krea 2 Turbo (9 st) seed 101: **PASS** [PP]  | OCR c2: FAIL `'FRESH\n\nBREAD\n\nBREAD\n\nDAILY\n\n7AM-2PM\n\n7AM-2PM'`
- Krea 2 Turbo (9 st) seed 102: **PASS** [PP]  | OCR c2: FAIL `'FRESH\nBREAD\n\nBREAD\nDAILY\n7AM-2PM\n\n7AM-ZPM'`
- MOSS-Image SFT (50 st) seed 101: **PASS** [PP]  | OCR c2: FAIL `'FRESH\n\nBREAD\n\nDAILY\n\n7.8m 2.5m\n\nDAILY\n\n7AM-2PM'`
- MOSS-Image SFT (50 st) seed 102: **PASS** [PP] extra small shop-window text 'Bakery-Cafe' outside the board | OCR c2: FAIL `'FRESH\n\nBREAD\n\nDAILY\n\n7AM-2DM\n\nDAILY\n\n7AM-2PM'`
- Qwen-Image-2.1 (40 st) seed 101: **PASS** [PP]  | OCR c2: PASS `'FRESH\n\nBREAD\n\nDAILY\n\n7AM-2PM\n\nUNIL\n\n7AM-2PM'`
- Qwen-Image-2.1 (40 st) seed 102: **PASS** [PP]  | OCR c2: PASS `'FRESH\n\nFRESH\n\nBREAD\n\nDAILY\n\n7AM-2PM\n\n7AM-2PM'`
- Qwen-Image-2512 (50 st) seed 101: **FAIL** [FP] adds a trailing period after 7AM-2PM | OCR c2: PASS `'FRESH\n\nFRESH\n\nBREAD\n\nDAILY\n\n7AM-2PM.\n\n7AM-2PM.'`
- Qwen-Image-2512 (50 st) seed 102: **FAIL** [FP] adds a trailing period after 7AM-2PM | OCR c2: PASS `'FRESH\n\nBREAD\n\nFRESH\n\nBREAD\n\nDAILY\n\n7AM-2PM.\n\n7AM-2PM.'`

### h5-handshake: Close-up of two people shaking hands, both hands fully visible.

Rubric: R1 exactly two hands are visible, one from each person (no third hand) | R2 each hand shows five fingers (four fingers and a thumb), none extra, missing or fused | R3 the grip is plausible (palms meet, thumbs wrap over, wrists connect to forearms)

- FIBO 2.0-dev (30 st) seed 101: **FAIL** [FPP] pulled back: the people's other hands hang at the sides (4 hands visible), shaking hands small and low-res
- FIBO 2.0-dev (30 st) seed 102: **FAIL** [FPP] pulled back again: the man's other hand hangs at the left (3+ hands visible), shaking hands small
- FLUX 3 Image Klein (16 st) seed 101: **PASS** [PPP] 
- FLUX 3 Image Klein (16 st) seed 102: **PASS** [PPP] 
- Krea 2 Turbo (9 st) seed 101: **PASS** [PPP] hands in soft focus
- Krea 2 Turbo (9 st) seed 102: **PASS** [PPP] smallish hands
- MOSS-Image SFT (50 st) seed 101: **PASS** [PPP] 
- MOSS-Image SFT (50 st) seed 102: **PASS** [PPP] 
- Qwen-Image-2.1 (40 st) seed 101: **PASS** [PPP] 
- Qwen-Image-2.1 (40 st) seed 102: **PASS** [PPP] 
- Qwen-Image-2512 (50 st) seed 101: **PASS** [PPP] 
- Qwen-Image-2512 (50 st) seed 102: **PASS** [PPP] 

### h6-clock345: A person holding an analogue wall clock that shows exactly 3:45.

Rubric: R1 a person holds a round analogue clock with a clock face | R2 the minute (long) hand points at the 9 (45 minutes) | R3 the hour (short) hand is between 3 and 4 (about three quarters of the way to the 4)

- FIBO 2.0-dev (30 st) seed 101: **FAIL** [PFP] four hands: long thick hand at 3, thin hands at 9 and 7; short hand between 3 and 4
- FIBO 2.0-dev (30 st) seed 102: **PASS** [PPP] long hand on 9, short hand between 3 and 4 (about 56 % of the way)
- FLUX 3 Image Klein (16 st) seed 101: **FAIL** [PFF] reads about 1:52; the thin hand near 9 is a second hand
- FLUX 3 Image Klein (16 st) seed 102: **FAIL** [PFF] hands at 8 (thin), about 9.7 and 1.5: not 3:45
- Krea 2 Turbo (9 st) seed 101: **FAIL** [PFF] reads about 10:10 (hour hand at 10, long hand at 2); a thin hand at 9
- Krea 2 Turbo (9 st) seed 102: **FAIL** [PFF] two long thick hands (9 and 2) and a short one at 3: not 3:45
- MOSS-Image SFT (50 st) seed 101: **FAIL** [PFP] one thick hand just past 3 (hour hand ok) and a thin long hand at about 10: minute hand not on 9
- MOSS-Image SFT (50 st) seed 102: **FAIL** [PPF] thin long hand on 9 but the short hand points to about 4.6, not between 3 and 4
- Qwen-Image-2.1 (40 st) seed 101: **PASS** [PPP] long hand on 9, short hand between 3 and 4 close to 4: reads 3:45
- Qwen-Image-2.1 (40 st) seed 102: **PASS** [PPP] long hand on 9, short hand between 3 and 4 but only a third of the way to the 4
- Qwen-Image-2512 (50 st) seed 101: **FAIL** [PFF] five hands, hour at 10, long hand at 2, extra hands at 6, 9 and 12
- Qwen-Image-2512 (50 st) seed 102: **FAIL** [PFF] three thick hands (9, 2 and 5) plus a thin one: no readable 3:45

