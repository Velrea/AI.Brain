"""The fictional stories the evals play against: one at home, one at work.

Each story is a list of steps in the order they were recorded, from June to
September 2026: entities, journal entries, filed documents, snapshots, and
the revisions that corrected or merged them. `seed.py` writes them through
the core module into the seeded Brain. Every name in them is invented.

Two laptops wrote them, `home` and `work`, so the seeded Brain holds event
files from two machines, as a synced Brain does.
"""

from dataclasses import dataclass, field


@dataclass
class Entity:
    slug: str
    on: str
    name: str
    kind: str
    body: str
    aliases: tuple[str, ...] = ()
    machine: str = "home"


@dataclass
class Journal:
    slug: str
    on: str
    description: str
    body: str
    links: tuple[str, ...]
    source: str = "voice"
    machine: str = "home"


@dataclass
class Document:
    """A document filed at `path` inside `documents/`: `contents`, then the
    boilerplate `footer`, which its entry's body leaves out."""
    slug: str
    on: str
    description: str
    path: str
    contents: str
    links: tuple[str, ...]
    footer: str = ""
    machine: str = "home"


@dataclass
class Snapshot:
    slug: str
    on: str
    description: str
    body: str
    links: tuple[str, ...]
    scope: str
    machine: str = "home"


@dataclass
class Revision:
    """A revision of the entry carrying the slug `of`, written on `on`."""
    of: str
    on: str
    type: str = "journal"
    fields: dict = field(default_factory=dict)
    machine: str = "home"


def merge(kept: str, other: str, on: str, aliases: tuple[str, ...] = (), machine: str = "home") -> Revision:
    """The entity revision that merges `other` into `kept`."""
    return Revision(kept, on, "entity", {"slug": other, "aliases": list(aliases)}, machine)


HOME = [
    # June
    Entity("wobblestone-cottage", "2026-06-01", "Wobblestone Cottage", "place",
           "Home: a thatched cottage at 14 Wobblestone Lane, Puddingshire, with a reading nook under the eaves"
           " and one chimney.", ("the cottage", "14 Wobblestone Lane", "the house")),
    Entity("glidemaster-hovercart", "2026-06-01", "Glidemaster 9 hovercart", "vehicle",
           "A purple Glidemaster 9 hovercart, bought used in 2024. Its odometer reads in leagues.",
           ("the hovercart", "the Glidemaster", "the cart")),
    Entity("gizmos-garage", "2026-06-01", "Gizmo's Garage", "company",
           "The hovercart mechanic on Sprocket Row, run by Gizmo Tinkerfoot.", ("Gizmo", "the garage")),
    Journal("2026-06-01-hovercart-float-inspection", "2026-06-01",
            "Hovercart passed its annual float inspection at Gizmo's Garage, 41,200 leagues",
            "## Inspection\nThe Glidemaster passed its annual float inspection at Gizmo's Garage.\n\n"
            "- Odometer: 41,200 leagues\n- Hover height: 14 inches, in spec\n- Cost: $95\n\n"
            "Gizmo said the anti-gravity coil hums a little and should be watched.",
            ("glidemaster-hovercart", "gizmos-garage")),
    Entity("potions", "2026-06-05", "Potions", "topic",
           "The potions Dr. Jekyll has the user take, and their doses.", ("my potions", "tonics")),
    Entity("dr-jekyll", "2026-06-05", "Dr. Jekyll", "person",
           "Henry Jekyll, the user's potion physician at the Lantern Street Apothecary.",
           ("Henry Jekyll", "Dr J", "the apothecary")),
    Entity("moonberry-tonic", "2026-06-05", "Moonberry tonic", "potion",
           "A tonic pressed from moonberries, taken in drops at night.", ("moonberry juice", "the tonic")),
    Entity("thistle-draught", "2026-06-05", "Thistle draught", "potion",
           "A bitter draught of thistle, taken by the spoonful in the morning.", ("the draught",)),
    Journal("2026-06-05-jekyll-glowing-ear", "2026-06-05",
            "Dr. Jekyll started moonberry tonic, 2 drops nightly, and thistle draught for my glowing left ear",
            "## Visit\nSaw Dr. Jekyll at the Lantern Street Apothecary about my left ear, which has glowed faintly"
            " green since May.\n\n## Potions\n- Moonberry tonic: 2 drops nightly\n- Thistle draught: 1 spoon"
            " each morning\n\n## Next\nFollow-up in about five weeks.",
            ("dr-jekyll", "potions", "moonberry-tonic", "thistle-draught")),
    Document("2026-06-05-jekyll-potion-instructions", "2026-06-05",
             "Dr. Jekyll's potion instructions: moonberry tonic 2 drops nightly, thistle draught 1 spoon mornings",
             "health/potions/2026-06-05-jekyll-potion-instructions.txt",
             "LANTERN STREET APOTHECARY\nPatient instructions, 5 June 2026\n\nMoonberry tonic: 2 drops under the"
             " tongue each night.\nThistle draught: 1 spoon each morning, with toast.\nDo not take either within"
             " an hour of singing.\nReturn in five weeks.\n",
             ("dr-jekyll", "moonberry-tonic", "thistle-draught", "potions"),
             footer="Dr. H. Jekyll, Lantern Street Apothecary, Puddingshire\n"),
    Journal("2026-06-07-planted-turnips", "2026-06-07",
            "Planted two rows of turnips in the cottage garden",
            "Planted two rows of Puddingshire purple turnips along the south wall of the cottage garden.",
            ("wobblestone-cottage",)),
    Entity("gnome-association", "2026-06-12", "Wobblestone Lane Gnome Association", "organization",
           "The lane's association of homeowners and their garden gnomes. It sets dues and gnome rules.",
           ("the gnome association", "WLGA", "the association")),
    Entity("mr-pumpernickel", "2026-06-12", "Mr. Pumpernickel", "person",
           "Barnaby Pumpernickel, the neighbour at number 9.", ("Barnaby Pumpernickel",)),
    Entity("mrs-grimsby", "2026-06-12", "Mrs. Grimsby", "person",
           "Agatha Grimsby, the neighbour at number 11, who keeps forty gnomes.", ("Agatha Grimsby",)),
    Journal("2026-06-12-gnome-association-meeting", "2026-06-12",
            "Gnome association meeting: dues up to $40 a quarter, garden gnomes capped at 3 feet",
            "## Meeting\nThe Wobblestone Lane Gnome Association met in Mr. Pumpernickel's garden. Mr. Pumpernickel"
            " chaired as president; Mrs. Grimsby took minutes.\n\n## Decided\n- Dues rise from $30 to $40 a"
            " quarter from July.\n- No garden gnome may stand taller than 3 feet.",
            ("gnome-association", "mr-pumpernickel", "mrs-grimsby", "wobblestone-cottage")),
    Entity("sir-fluffington", "2026-06-15", "Sir Fluffington", "pet",
           "The user's teacup dragon, green with a white belly.", ("Fluff", "my dragon")),
    Entity("dr-jellybean", "2026-06-15", "Dr. Jellybean", "person",
           "Penelope Jellybean, the dragon vet at Ember Lane Veterinary.",
           ("Penelope Jellybean", "Dr J", "the dragon vet")),
    Journal("2026-06-15-fluffington-checkup", "2026-06-15",
            "Sir Fluffington's checkup with Dr. Jellybean: 4.2 lb, scales shiny, flame a healthy orange",
            "## Checkup\nDr. Jellybean saw Sir Fluffington at Ember Lane Veterinary.\n\n- Weight: 4.2 lb\n"
            "- Scales: shiny\n- Flame: healthy orange\n\nShe said to keep him off scented candles.",
            ("sir-fluffington", "dr-jellybean")),
    Journal("2026-06-19-fluffington-fetch", "2026-06-19",
            "Sir Fluffington learned to fetch, but only pinecones",
            "Taught Sir Fluffington to fetch. He brings back pinecones and nothing else, and toasts them first.",
            ("sir-fluffington",)),
    Entity("chimney-goblin", "2026-06-20", "The chimney goblin", "pest",
           "A goblin that gets into the cottage through the chimney and steals socks.", ("the goblin",)),
    Journal("2026-06-20-chimney-goblin-first-visit", "2026-06-20",
            "Chimney goblin got in for the first time and stole eleven socks",
            "Woke to soot on the hearth and eleven socks gone from the drying rack. A goblin came down the"
            " chimney in the night; Sir Fluffington chased it back up.",
            ("chimney-goblin", "wobblestone-cottage", "sir-fluffington")),
    Entity("thatch-and-sons", "2026-06-25", "Thatch & Sons", "company",
           "Roofers and chimney sweeps in Puddingshire, run by Old Man Thatch.", ("Thatch and Sons", "the roofers")),
    Journal("2026-06-25-roof-leak-reading-nook", "2026-06-25",
            "Roof leaked over the reading nook; Thatch & Sons patched the thatch for $210",
            "Rain came through the thatch over the reading nook. Thatch & Sons came the same afternoon and patched"
            " it: $210, paid on the spot.",
            ("wobblestone-cottage", "thatch-and-sons")),
    Entity("the-dragon", "2026-06-28", "The dragon", "pet",
           "The dragon that set the curtains on fire.", ()),
    Journal("2026-06-28-dragon-curtain-fire", "2026-06-28",
            "The dragon set the sitting-room curtains on fire; new curtains cost $85",
            "He sneezed at the curtains after sniffing pepper. Put it out with the kettle. New curtains from"
            " Puddingshire market: $85.",
            ("the-dragon", "wobblestone-cottage")),
    # July
    merge("sir-fluffington", "the-dragon", "2026-07-01", ("the dragon",)),
    Entity("floatwell-insurance", "2026-07-02", "Floatwell Insurance", "company",
           "Insures the hovercart.", ("Floatwell",)),
    Journal("2026-07-02-hovercart-insurance-renewal", "2026-07-02",
            "Renewed the hovercart insurance with Floatwell: $310 for six months, policy FW-77-ZB",
            "Renewed with Floatwell Insurance for July to December. $310 for the half year, policy FW-77-ZB,"
            " $250 excess. Covers collisions with low-flying geese.",
            ("glidemaster-hovercart", "floatwell-insurance")),
    Document("2026-07-02-floatwell-policy", "2026-07-02",
             "Floatwell hovercart policy FW-77-ZB, July to December 2026, $310, $250 excess",
             "vehicles/glidemaster-hovercart/insurance/2026-07-02-floatwell-policy.txt",
             "FLOATWELL INSURANCE\nPolicy FW-77-ZB\n\nVehicle: Glidemaster 9 hovercart, purple\nPeriod: 1 July 2026"
             " to 31 December 2026\nPremium: $310\nExcess: $250\nCovered: collision, theft, low-flying geese\n"
             "Not covered: flight above 40 feet\n",
             ("glidemaster-hovercart", "floatwell-insurance"),
             footer="Floatwell Insurance. Keep this policy in the hovercart.\n"),
    Journal("2026-07-05-pumpernickel-gnome-party", "2026-07-05",
            "Went to Mr. Pumpernickel's gnome garden party",
            "Mr. Pumpernickel threw a garden party for the lane's gnomes. Brought turnip crisps. Mrs. Grimsby"
            " brought six of her gnomes.",
            ("mr-pumpernickel", "mrs-grimsby", "gnome-association")),
    Journal("2026-07-10-jekyll-follow-up", "2026-07-10",
            "Dr. Jekyll raised moonberry tonic to 4 drops nightly; ear still glows faintly",
            "Follow-up at the Lantern Street Apothecary. The ear glows less but still shows in the dark.\n\n"
            "## Potions\n- Moonberry tonic: up from 2 to 4 drops nightly\n- Thistle draught: unchanged, 1 spoon"
            " each morning",
            ("dr-jekyll", "potions", "moonberry-tonic", "2026-06-05-jekyll-glowing-ear")),
    Journal("2026-07-14-hovercart-wash", "2026-07-14",
            "Hovercart wash and wax at Bubble Bay, $20",
            "Took the Glidemaster through the Bubble Bay wash and wax: $20. The purple is shiny again.",
            ("glidemaster-hovercart",)),
    Journal("2026-07-18-grimsby-elected-president", "2026-07-18",
            "Mrs. Grimsby elected gnome association president; Mr. Pumpernickel stepped down to treasurer",
            "At a special meeting of the gnome association, Mr. Pumpernickel stepped down as president, citing"
            " his gout. Mrs. Grimsby was elected president, 14 votes to 3. Mr. Pumpernickel became treasurer.",
            ("gnome-association", "mrs-grimsby", "mr-pumpernickel")),
    Journal("2026-07-22-chimney-goblin-back", "2026-07-22",
            "Chimney goblin back a second time; Thatch & Sons quoted $620 for a goblin-proof chimney cap",
            "The goblin came back and took the oven mitts. Old Man Thatch came round and quoted $620 for a"
            " goblin-proof brass chimney cap, fitted in August.",
            ("chimney-goblin", "wobblestone-cottage", "thatch-and-sons", "2026-06-20-chimney-goblin-first-visit")),
    Journal("2026-07-26-fluffington-moth", "2026-07-26",
            "Sir Fluffington caught a moth and singed the lampshade",
            "He caught a moth in mid-air and singed the reading-nook lampshade doing it. Lampshade survives.",
            ("sir-fluffington", "wobblestone-cottage")),
    Journal("2026-07-30-moonberry-bush", "2026-07-30",
            "Bought a moonberry bush for the cottage garden, $35",
            "Bought a moonberry bush at Puddingshire market for $35 and planted it by the gate. It should fruit"
            " next summer.",
            ("wobblestone-cottage",)),
    # August
    Snapshot("current-potions-2026-08-01", "2026-08-01",
             "Current potions: moonberry tonic 4 drops nightly, thistle draught 1 spoon mornings",
             "As of 1 August 2026:\n\n- Moonberry tonic: 4 drops nightly (2026-07-10, Dr. Jekyll raised it from 2)\n"
             "- Thistle draught: 1 spoon each morning (2026-06-05, Dr. Jekyll started it)",
             ("potions", "dr-jekyll"), "current potions and their doses"),
    Journal("2026-08-01-gnome-dues-paid", "2026-08-01",
            "Paid the gnome association's $40 dues for July to September",
            "Paid Mr. Pumpernickel, as treasurer, the $40 quarterly dues for July to September.",
            ("gnome-association", "mr-pumpernickel")),
    Entity("anti-gravity-coil", "2026-08-05", "Anti-gravity coil", "part",
           "The part that keeps the hovercart up.", ("the coil",)),
    Journal("2026-08-05-hovercart-coil-replaced", "2026-08-05",
            "Gizmo's Garage replaced the hovercart's humming anti-gravity coil, $1,240 at 43,900 leagues",
            "The coil had started humming in B-flat. Gizmo's Garage replaced it.\n\n- Odometer: 43,900 leagues\n"
            "- Cost: $1,240, parts and labour\n- Warranty: 2 years on the new coil",
            ("glidemaster-hovercart", "gizmos-garage", "anti-gravity-coil", "2026-06-01-hovercart-float-inspection")),
    Document("2026-08-05-coil-replacement-invoice", "2026-08-05",
             "Gizmo's Garage invoice: anti-gravity coil replaced, $1,240 at 43,900 leagues",
             "vehicles/glidemaster-hovercart/service/2026-08-05-coil-replacement-invoice.txt",
             "GIZMO'S GARAGE\nInvoice 2207, 5 August 2026\n\nGlidemaster 9 hovercart, 43,900 leagues\nAnti-gravity"
             " coil, new: $980\nLabour, 2 hours: $260\nTotal: $1,240\nWarranty on coil: 2 years\n",
             ("glidemaster-hovercart", "gizmos-garage", "anti-gravity-coil"),
             footer="Thank you for floating with Gizmo's.\n"),
    Journal("2026-08-08-hovercart-parking-ticket", "2026-08-08",
            "$15 parking ticket for leaving the hovercart floating over the vicar's hedge",
            "Left the Glidemaster hovering over the vicarage hedge during the fete. $15 ticket from the parish"
            " warden. Paid it.",
            ("glidemaster-hovercart",)),
    Journal("2026-08-12-chimney-cap-installed", "2026-08-12",
            "Thatch & Sons fitted the goblin-proof chimney cap, $640 with brass fixings",
            "Thatch & Sons fitted the goblin-proof brass chimney cap. $640: the $620 quote plus $20 of brass"
            " fixings. Guaranteed goblin-proof for a year.",
            ("wobblestone-cottage", "thatch-and-sons", "chimney-goblin", "2026-07-22-chimney-goblin-back")),
    Document("2026-08-12-chimney-cap-invoice", "2026-08-12",
             "Thatch & Sons invoice: goblin-proof chimney cap, $640, guaranteed a year",
             "home/wobblestone-cottage/roof/2026-08-12-chimney-cap-invoice.txt",
             "THATCH & SONS\nInvoice 88, 12 August 2026\n\nWobblestone Cottage, 14 Wobblestone Lane\nGoblin-proof"
             " brass chimney cap, fitted: $620\nBrass fixings: $20\nTotal: $640\nGuarantee: goblin-proof for one"
             " year from fitting\n",
             ("wobblestone-cottage", "thatch-and-sons", "chimney-goblin"),
             footer="Thatch & Sons, since 1802.\n"),
    Entity("starlight-syrup", "2026-08-20", "Starlight syrup", "potion",
           "A sweet syrup taken by the teaspoon at lunch.", ("the syrup",)),
    Journal("2026-08-20-jekyll-stopped-thistle", "2026-08-20",
            "Dr. Jekyll stopped the thistle draught over the bubble hiccups and started starlight syrup",
            "The thistle draught gave me hiccups that come out as bubbles. Dr. Jekyll stopped it and started"
            " starlight syrup instead.\n\n## Potions\n- Thistle draught: stopped\n- Starlight syrup: 1 teaspoon"
            " at lunch\n- Moonberry tonic: unchanged, 4 drops nightly",
            ("dr-jekyll", "potions", "thistle-draught", "starlight-syrup", "moonberry-tonic")),
    Journal("2026-08-26-fluffington-checkup", "2026-08-26",
            "Sir Fluffington's checkup: 4.9 lb, switched to ember-free kibble",
            "Dr. Jellybean weighed him at 4.9 lb, up from 4.2 in June. She switched him to ember-free kibble,"
            " a scoop morning and night, and said his flame is fine.",
            ("sir-fluffington", "dr-jellybean", "2026-06-15-fluffington-checkup")),
    Document("2026-08-26-jellybean-checkup-notes", "2026-08-26",
             "Dr. Jellybean's checkup notes for Sir Fluffington: 4.9 lb, ember-free kibble",
             "pets/sir-fluffington/vet/2026-08-26-jellybean-checkup-notes.txt",
             "EMBER LANE VETERINARY\nPatient: Sir Fluffington, teacup dragon\nDate: 26 August 2026\n\nWeight: 4.9"
             " lb (4.2 lb in June)\nFlame: orange, steady\nDiet: ember-free kibble, one scoop morning and night\n"
             "Next visit: February 2027\n",
             ("sir-fluffington", "dr-jellybean"),
             footer="Dr. P. Jellybean\n"),
    Journal("2026-08-29-moonberry-tonic-refill", "2026-08-29",
            "Refilled the moonberry tonic at the Lantern Street Apothecary, $18",
            "Picked up a new bottle of moonberry tonic at the Lantern Street Apothecary: $18 for 120 drops.",
            ("moonberry-tonic", "potions")),
    # September
    Document("2026-09-02-gnome-height-notice-letter", "2026-09-02",
             "Gnome association notice: Bartholomew is 3.5 ft, over the 3-ft cap; $25 fine, waived if fixed by"
             " 2026-09-30",
             "home/wobblestone-cottage/gnome-association/2026-09-02-gnome-height-notice.txt",
             "WOBBLESTONE LANE GNOME ASSOCIATION\nNotice of breach, 2 September 2026\n\nTo: 14 Wobblestone Lane\n"
             "Gnome: Bartholomew, measured at 3.5 feet\nRule: no garden gnome may stand taller than 3 feet\nFine:"
             " $25, waived if the gnome is brought under 3 feet by 30 September 2026\n\nAgatha Grimsby, President\n",
             ("gnome-association", "mrs-grimsby", "wobblestone-cottage"),
             footer="Gnomes are neighbours too.\n"),
    Journal("2026-09-02-gnome-height-notice", "2026-09-02",
            "Gnome association fined me $25: my gnome Bartholomew stands 3.5 feet, over the 3-foot cap",
            "A notice from the gnome association, signed by Mrs. Grimsby as president: my gnome Bartholomew"
            " stands 3.5 feet, over the 3-foot cap. Fine of $25, waived if he is brought under 3 feet by"
            " 2026-09-30.",
            ("gnome-association", "mrs-grimsby", "wobblestone-cottage", "2026-09-02-gnome-height-notice-letter")),
    Journal("2026-09-05-grimsby-gnome-tea", "2026-09-05",
            "Tea with Mrs. Grimsby and her gnomes; she hinted the fine could be waived",
            "Mrs. Grimsby had me over for tea among her forty gnomes. She hinted the $25 fine goes away if"
            " Bartholomew loses a few inches.",
            ("mrs-grimsby", "2026-09-02-gnome-height-notice")),
    Journal("2026-09-09-gnome-hat-trimmed", "2026-09-09",
            "Trimmed Bartholomew's hat to 2.9 feet; Mrs. Grimsby waived the $25 fine",
            "Took two inches off Bartholomew's hat with a hacksaw; he now stands 2.9 feet. Mrs. Grimsby came"
            " round with a tape measure and waived the $25 fine.",
            ("gnome-association", "mrs-grimsby", "2026-09-02-gnome-height-notice")),
    Journal("2026-09-12-turnip-harvest", "2026-09-12",
            "Harvested 9 lb of turnips from the cottage garden",
            "Pulled the turnips planted in June: 9 lb, one of them shaped like Mr. Pumpernickel.",
            ("wobblestone-cottage", "2026-06-07-planted-turnips")),
    Journal("2026-09-15-jekyll-lowered-tonic", "2026-09-15",
            "Dr. Jekyll lowered moonberry tonic to 3 drops nightly; the ear has stopped glowing",
            "The ear has stopped glowing, even in the dark. Dr. Jekyll lowered the moonberry tonic from 4 to 3"
            " drops nightly. Starlight syrup stays at 1 teaspoon at lunch. Next visit in December.",
            ("dr-jekyll", "potions", "moonberry-tonic", "starlight-syrup")),
    Journal("2026-09-18-chimney-goblin-third-visit", "2026-09-18",
            "Chimney goblin got past the new cap, a third visit; Thatch & Sons to return 2026-10-08 under guarantee",
            "The goblin got in again, past the new cap, and took the tea cosy. Third time this year. Old Man"
            " Thatch says the cap is under its one-year guarantee and will come back on 2026-10-08 to fit a"
            " finer mesh at no charge.",
            ("chimney-goblin", "wobblestone-cottage", "thatch-and-sons", "2026-08-12-chimney-cap-installed")),
    Journal("2026-09-24-hovercart-pulling-left", "2026-09-24",
            "Hovercart pulled left; Gizmo's Garage re-trimmed the hover jets for free",
            "The Glidemaster drifted left on the high street. Gizmo re-trimmed the left hover jets in ten"
            " minutes, no charge, as part of the coil warranty.",
            ("glidemaster-hovercart", "gizmos-garage", "2026-08-05-hovercart-coil-replaced")),
    Journal("2026-09-26-starlight-syrup-refill", "2026-09-26",
            "Refilled the starlight syrup, $12",
            "Bought another bottle of starlight syrup at the Lantern Street Apothecary: $12.",
            ("starlight-syrup", "potions")),
    Journal("2026-09-27-dragon-ate-candle", "2026-09-27",
            "Sir Fluffington ate a scented candle; Dr. Jellybean said to watch him, no visit needed",
            "He ate a lavender candle off the windowsill. Rang Dr. Jellybean: watch for purple smoke, no visit"
            " needed unless it lasts past Tuesday.",
            ("sir-fluffington", "dr-jellybean")),
    Revision("2026-06-01-hovercart-float-inspection", "2026-09-28",
             fields={"description": "Hovercart passed its annual float inspection at Gizmo's Garage, 41,020 leagues",
                     "body": "Correction: the odometer read 41,020 leagues, not 41,200. Checked the inspection"
                             " sticker."}),
]

WORK = [
    # June
    Entity("zorblax-industries", "2026-06-02", "Zorblax Industries", "company",
           "The user's employer, maker of improbable kitchen machines.", ("Zorblax", "work"), "work"),
    Entity("project-moonbeam", "2026-06-02", "Project Moonbeam", "project",
           "Zorblax's moonberry juice extractor that runs on moonlight.", ("Moonbeam", "the extractor"), "work"),
    Entity("prof-quibblesworth", "2026-06-02", "Professor Quibblesworth", "person",
           "Ignatius Quibblesworth, the user's manager at Zorblax Industries.",
           ("Quibblesworth", "Ignatius Quibblesworth", "my manager"), "work"),
    Journal("2026-06-02-moonbeam-planning", "2026-06-02",
            "Moonbeam planning with Prof. Quibblesworth: prototype extractor by 2026-10-31 on a $50,000 budget",
            "## Planning\nProfessor Quibblesworth set Project Moonbeam's goal: a working prototype of the moonlight"
            " juice extractor by 2026-10-31.\n\n- Budget: $50,000\n- Team: me and an intern, to be hired\n"
            "- Target juice yield: 75% of the berry",
            ("project-moonbeam", "prof-quibblesworth", "zorblax-industries"), "meeting", "work"),
    Entity("nimbus-pratt", "2026-06-09", "Nimbus Pratt", "person",
           "The summer intern on Project Moonbeam.", ("Nimbus", "the intern"), "work"),
    Journal("2026-06-09-nimbus-started", "2026-06-09",
            "Nimbus Pratt started as the Moonbeam intern",
            "Nimbus Pratt started today as the summer intern on Project Moonbeam, through 2026-09-12. Set up their"
            " desk next to the berry fridge.",
            ("nimbus-pratt", "project-moonbeam"), "meeting", "work"),
    Journal("2026-06-12-zorblax-all-hands", "2026-06-12",
            "Zorblax all-hands: Madame Zorblax named Moonbeam one of the year's three bets",
            "At the all-hands, Madame Zorblax named Project Moonbeam one of the company's three bets for the"
            " year, beside the self-buttering toaster and the polite kettle.",
            ("zorblax-industries", "project-moonbeam"), "meeting", "work"),
    Journal("2026-06-17-quibblesworth-one-on-one", "2026-06-17",
            "1:1 with Quibblesworth: I own the moonlight-capture lens, Nimbus owns the juicing chamber",
            "## Decided\n- I own the moonlight-capture lens.\n- Nimbus Pratt owns the juicing chamber.\n\n"
            "## Commitments\n- Me: lens design draft to Quibblesworth by 2026-06-30.",
            ("prof-quibblesworth", "project-moonbeam", "nimbus-pratt"), "meeting", "work"),
    Entity("glorp-logistics", "2026-06-23", "Glorp Logistics", "company",
           "The freight company that ships moonberries to Zorblax.", ("Glorp",), "work"),
    Entity("speedy-snail-couriers", "2026-06-23", "Speedy Snail Couriers", "company",
           "A cheap, slow courier.", ("Speedy Snail",), "work"),
    Journal("2026-06-23-moonberry-shipper-chosen", "2026-06-23",
            "Chose Glorp Logistics over Speedy Snail to ship moonberries: $2.10 a crate, 3 days versus 9 weeks",
            "## Decided\nGlorp Logistics ships the moonberries.\n\n- Glorp: $2.10 a crate, 3 days door to door\n"
            "- Speedy Snail Couriers: $1.80 a crate, about 9 weeks, by which time the berries are jam\n\n"
            "Quibblesworth agreed.",
            ("glorp-logistics", "speedy-snail-couriers", "project-moonbeam", "prof-quibblesworth"), "meeting", "work"),
    Journal("2026-06-26-moonbeam-standup", "2026-06-26",
            "Moonbeam standup: Nimbus ordered the first 600 crates of moonberries",
            "Nimbus ordered the first 600 crates of moonberries for July. I'm still on the lens draft.",
            ("project-moonbeam", "nimbus-pratt"), "meeting", "work"),
    Journal("2026-06-30-lens-design-draft", "2026-06-30",
            "Sent the moonlight-capture lens design draft to Quibblesworth, on time",
            "Sent the lens design draft to Professor Quibblesworth: a glass lens 30 cm across, focused on the"
            " juicing chamber.",
            ("project-moonbeam", "prof-quibblesworth", "2026-06-17-quibblesworth-one-on-one"), "email", "work"),
    # July
    Document("2026-07-01-glorp-logistics-contract", "2026-07-01",
             "Glorp Logistics contract: $2.10 a crate, 500 crates a month minimum, 30 days' notice to end",
             "work/project-moonbeam/contracts/2026-07-01-glorp-logistics-contract.txt",
             "FREIGHT AGREEMENT\nBetween Glorp Logistics and Zorblax Industries, from 1 July 2026\n\nGoods: fresh"
             " moonberries, in crates\nRate: $2.10 a crate\nMinimum: 500 crates a month\nDelivery: 3 days door to"
             " door\nDamage: Glorp pays for crates it damages\nTermination: either party, on 30 days' written"
             " notice\n",
             ("glorp-logistics", "zorblax-industries", "project-moonbeam"),
             footer="Signed for Glorp Logistics and for Zorblax Industries.\n", machine="work"),
    Journal("2026-07-01-glorp-contract-signed", "2026-07-01",
            "Signed the Glorp Logistics freight contract for moonberries",
            "Signed the freight agreement with Glorp Logistics, from today: $2.10 a crate, at least 500 crates a"
            " month, 30 days' notice to end it.",
            ("glorp-logistics", "project-moonbeam", "2026-07-01-glorp-logistics-contract",
             "2026-06-23-moonberry-shipper-chosen"), "email", "work"),
    Journal("2026-07-08-moonbeam-design-review", "2026-07-08",
            "Moonbeam design review: glass lens won't focus moonlight; switching to quartz, mine by 2026-07-29",
            "## Problem\nThe glass lens scatters moonlight and won't focus it on the chamber.\n\n## Decided\nSwitch"
            " to a quartz lens. I order it and fit it by 2026-07-29.",
            ("project-moonbeam", "prof-quibblesworth", "nimbus-pratt"), "meeting", "work"),
    Journal("2026-07-15-juicing-chamber-leak", "2026-07-15",
            "Juicing chamber leaked moonberry juice onto the lab floor; Nimbus resealing it",
            "The juicing chamber leaked a litre of juice across the lab floor. Nimbus is resealing it with"
            " food-grade wax this week.",
            ("project-moonbeam", "nimbus-pratt"), "meeting", "work"),
    Journal("2026-07-21-quibblesworth-one-on-one", "2026-07-21",
            "1:1 with Quibblesworth: I'll present Moonbeam at the September board demo",
            "Quibblesworth asked me to present Project Moonbeam to the board at the demo in early September."
            " We talked about what a promotion case would need: a working prototype and a happy board.",
            ("prof-quibblesworth", "project-moonbeam"), "meeting", "work"),
    Journal("2026-07-29-quartz-lens-fitted", "2026-07-29",
            "Fitted the quartz lens: moonlight focuses, first juice yield 62%",
            "Fitted the quartz lens. Moonlight now focuses on the chamber, and the first full run pressed 62% of"
            " the berry into juice.",
            ("project-moonbeam", "2026-07-08-moonbeam-design-review"), "meeting", "work"),
    # August
    Journal("2026-08-04-glorp-shipment-late", "2026-08-04",
            "Glorp shipment 3 days late with 40 crates squished; filed a claim",
            "The weekly Glorp Logistics shipment came 3 days late, and 40 of the 600 crates were squished."
            " Filed a damage claim with Glorp.",
            ("glorp-logistics", "project-moonbeam"), "email", "work"),
    Entity("glorp-co", "2026-08-11", "Glorp Co", "company",
           "Sent an invoice for the squished crates.", ("Glorp Co.",), "work"),
    Document("2026-08-11-glorp-co-crate-invoice", "2026-08-11",
             "Glorp Co invoice: $84 for 40 squished moonberry crates",
             "work/project-moonbeam/invoices/2026-08-11-glorp-co-crate-invoice.txt",
             "GLORP CO\nInvoice G-4410, 11 August 2026\n\nTo: Zorblax Industries\nCrates damaged in transit: 40\n"
             "Charge: $2.10 a crate\nTotal: $84\n",
             ("glorp-co", "project-moonbeam"),
             footer="Pay within 14 days.\n", machine="work"),
    Journal("2026-08-11-glorp-co-invoice-dispute", "2026-08-11",
            "Disputing Glorp Co's $84 charge for the 40 squished crates",
            "Nimbus forwarded an invoice from Glorp Co charging us $84 for the 40 crates that came squished."
            " Disputed it: the damage was in transit.",
            ("glorp-co", "nimbus-pratt", "2026-08-04-glorp-shipment-late", "2026-08-11-glorp-co-crate-invoice"),
            "email", "work"),
    Journal("2026-08-19-moonbeam-budget-review", "2026-08-19",
            "Moonbeam budget review: $31,400 of $50,000 spent; Quibblesworth approved $5,000 more for a second lens",
            "## Budget\n- Spent: $31,400 of $50,000\n- Approved: $5,000 more, for a second quartz lens, so the"
            " budget is now $55,000",
            ("project-moonbeam", "prof-quibblesworth"), "meeting", "work"),
    Document("2026-08-19-moonbeam-budget-sheet", "2026-08-19",
             "Moonbeam budget sheet: $31,400 spent of $55,000",
             "work/project-moonbeam/budget/2026-08-19-moonbeam-budget-sheet.txt",
             "PROJECT MOONBEAM BUDGET, 19 August 2026\n\nLenses: $9,800\nJuicing chamber: $12,600\nMoonberries:"
             " $6,300\nFreight: $2,700\nSpent: $31,400\nBudget: $55,000, after $5,000 approved for a second lens\n",
             ("project-moonbeam",),
             footer="Zorblax Industries, internal.\n", machine="work"),
    Snapshot("moonbeam-status-2026-08-20", "2026-08-20",
             "Moonbeam status: quartz lens fitted, yield 62%, $31,400 of $55,000 spent, prototype due 2026-10-31",
             "As of 20 August 2026:\n\n- Yield: 62% (2026-07-29, quartz lens fitted)\n- Budget: $31,400 spent of"
             " $55,000 (2026-08-19)\n- Prototype due: 2026-10-31 (2026-06-02)",
             ("project-moonbeam",), "project moonbeam status", "work"),
    Journal("2026-08-25-glorp-co-is-glorp", "2026-08-25",
            "Glorp Logistics confirmed Glorp Co is their billing name and cancelled the $84 charge",
            "Glorp Logistics called back about the dispute: Glorp Co is just the name their billing office uses."
            " They cancelled the $84 charge and paid our claim for the squished crates.",
            ("glorp-logistics", "glorp-co", "2026-08-11-glorp-co-invoice-dispute"), "email", "work"),
    Journal("2026-08-28-zorblax-offsite", "2026-08-28",
            "Zorblax offsite at the Cheese Caves",
            "Team offsite at the Cheese Caves. Quibblesworth won the fondue relay. Nimbus fell in the brie.",
            ("zorblax-industries", "prof-quibblesworth", "nimbus-pratt"), "meeting", "work"),
    # September
    Journal("2026-09-02-moonbeam-board-demo", "2026-09-02",
            "Demoed Moonbeam to the Zorblax board: 71% yield; board wants a glow-in-the-dark variant",
            "## Demo\nShowed the Zorblax board the extractor running on moonlight from the roof. Juice yield 71%.\n\n"
            "## Asked\nThe board wants a glow-in-the-dark juice variant.",
            ("project-moonbeam", "zorblax-industries", "prof-quibblesworth"), "meeting", "work"),
    Journal("2026-09-04-quibblesworth-demo-feedback", "2026-09-04",
            "Quibblesworth said the board demo went well and the glow variant is mine",
            "Quibblesworth said the board liked the demo, and that the glow-in-the-dark variant is mine to scope.",
            ("prof-quibblesworth", "project-moonbeam", "2026-09-02-moonbeam-board-demo"), "meeting", "work"),
    Journal("2026-09-10-nimbus-review", "2026-09-10",
            "Nimbus Pratt's internship review: recommended a return offer",
            "Wrote Nimbus Pratt's end-of-internship review. The juicing chamber works and doesn't leak. Recommended"
            " a return offer for next summer.",
            ("nimbus-pratt", "prof-quibblesworth", "project-moonbeam"), "meeting", "work"),
    Journal("2026-09-12-nimbus-last-day", "2026-09-12",
            "Nimbus Pratt's last day; farewell cake shaped like the extractor",
            "Nimbus's last day. The team got a cake shaped like the extractor; it leaked custard, which felt right.",
            ("nimbus-pratt", "project-moonbeam"), "meeting", "work"),
    Journal("2026-09-16-quibblesworth-glow-spec", "2026-09-16",
            "1:1 with Quibblesworth: I'll write the glow-in-the-dark variant spec by 2026-10-15",
            "## Commitments\n- Me: the glow-in-the-dark juice variant spec, to Quibblesworth by 2026-10-15.\n\n"
            "## Open\n- Whether glowing juice needs a warning label.",
            ("prof-quibblesworth", "project-moonbeam", "2026-09-02-moonbeam-board-demo"), "meeting", "work"),
    Journal("2026-09-22-glorp-quarterly-review", "2026-09-22",
            "Glorp quarterly review: rate rises to $2.35 a crate from 2026-11-01; weighing Speedy Snail again",
            "Glorp Logistics is raising its rate from $2.10 to $2.35 a crate from 2026-11-01. Asked Speedy Snail"
            " Couriers for a faster quote before deciding.",
            ("glorp-logistics", "speedy-snail-couriers", "project-moonbeam"), "meeting", "work"),
    Journal("2026-09-25-glow-variant-research", "2026-09-25",
            "Started glow variant research: glowworm-free luminescence from moon algae",
            "Started on the glow-in-the-dark variant. Glowworms are out; moon algae glow without them and taste"
            " of cucumber.",
            ("project-moonbeam", "2026-09-16-quibblesworth-glow-spec"), "meeting", "work"),
    Journal("2026-09-29-second-lens-yield", "2026-09-29",
            "Second quartz lens fitted: juice yield up to 78%, past the 75% target",
            "Fitted the second quartz lens. The extractor now presses 78% of the berry into juice, past the 75%"
            " target.",
            ("project-moonbeam", "2026-08-19-moonbeam-budget-review"), "meeting", "work"),
    Journal("2026-09-30-speedy-snail-quote", "2026-09-30",
            "Speedy Snail quoted $1.95 a crate in 6 weeks; still too slow for fresh moonberries",
            "Speedy Snail Couriers came back at $1.95 a crate, 6 weeks door to door. Berries would still arrive"
            " as jam. Staying with Glorp for now.",
            ("speedy-snail-couriers", "glorp-logistics", "2026-09-22-glorp-quarterly-review"), "email", "work"),
]

STORIES = {"home": HOME, "work": WORK}

INBOX = {
    # Files handed over in the filing cases, by name.
    "2026-09-24-gizmo-hover-trim-receipt.txt":
        "GIZMO'S GARAGE\nReceipt 2391, 24 September 2026\n\nGlidemaster 9 hovercart\nLeft hover jets re-trimmed\n"
        "Charge: $0, under coil warranty\n\nThank you for floating with Gizmo's.\n",
    "2026-09-22-glorp-rate-letter.txt":
        "GLORP LOGISTICS\n22 September 2026\n\nTo: Zorblax Industries\nFrom 1 November 2026 our rate rises from"
        " $2.10 to $2.35 a crate. All other terms of the freight agreement are unchanged.\n",
    "2026-10-01-gnome-dues-receipt.txt":
        "WOBBLESTONE LANE GNOME ASSOCIATION\nReceipt, 1 October 2026\n\nFrom: 14 Wobblestone Lane\nDues, October"
        " to December: $40\n\nB. Pumpernickel, Treasurer\n",
    "telescope-warranty.txt":
        "ORBIGLASS TELESCOPES\nWarranty card\n\nModel: Orbiglass 200\nBought: 20 September 2026\nWarranty: 5 years,"
        " lenses and mount\n",
    # Pointers: a shared spreadsheet's, of a format no real product uses, and a
    # shortcut to a file in the run's own folder.
    "moonbeam-budget-tracker.zsheet":
        '{"doc_id": "7Qx2mB9kLr", "url": "https://sheets.zorblax.invalid/d/7Qx2mB9kLr"}\n',
    "coil-warranty.url":
        "[InternetShortcut]\nURL={workspace}/elsewhere/2026-08-05-coil-warranty-certificate.txt\n",
}

ELSEWHERE = {
    # Files kept outside the inbox that a pointer in it names, by name.
    "2026-08-05-coil-warranty-certificate.txt":
        "GIZMO'S GARAGE\nWarranty certificate, 5 August 2026\n\nGlidemaster 9 hovercart\nAnti-gravity coil, new,"
        " fitted at 43,900 leagues\nWarranty: 2 years, parts and labour, to 5 August 2028\n",
}
"""Files handed over in the filing cases. The coil invoice already filed is
handed over again, as a copy, by `cases.py`."""
