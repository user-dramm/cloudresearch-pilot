/* ============================================================================
   DEMO CONFIG: a preview build for colleagues to walk. NOT the study.
   ----------------------------------------------------------------------------
   Lives at /demo/ so it can never be confused with the real instrument at the
   site root. Deliberately different from the real config.js in four ways:

     studyTag     "demo-2026-08", not "pilot-2026-07". This is the important one.
                  The demo posts to the SAME endpoint and the same Sheet, and
                  analysis.py drops any row whose study_tag is not the real one -
                  so a colleague clicking through cannot contaminate the dataset
                  even if they never touch ?selftest=1. Relying on people to
                  remember a URL parameter is not a control.

     watchGate    0.05 instead of 0.90, so a reviewer clears each video in about
                  15 seconds rather than four minutes - roughly a minute of watching
                  across all four. The banner says so on screen; without that a
                  reviewer would reasonably report the gate as broken.

     demoBanner   a visible notice on every screen. A reviewer who believes they
                  are seeing the real study gives feedback on the wrong thing.

     videos       the REAL joined uploads, two of them, so a reviewer sees exactly
                  what a rater sees. They are two DIFFERENT courses rather than two
                  versions of one, so "which was better" means nothing here. Both are
                  the current build, so nothing about old-vs-new is on display either.

   The completion code is blanked: nothing here should hand out a payable code.
   ============================================================================ */

window.STUDY_CONFIG = {

  studyTag: "demo-2026-08",

  videoSource: "youtube",
  blockSeeking: true,

  endpoint: "https://script.google.com/macros/s/AKfycbzlJjh67g33lmEEJslD9JhMhKQj3lulof4UAXlZ12auC4_7D7DX4DEQskGpdES2n3Zx/exec",

  formToken: "embr-pilot-2026-07",

  /* No payable code from a preview. */
  completionCode: "DEMO-NO-CODE",
  redirectUrl: "",

  /* 5% instead of 90%. NOT the study value - see the banner. */
  watchGate: 0.05,

  minCommentChars: 60,
  minWhyChars: 80,

  demoBanner:
    "<strong>Preview, not the real study.</strong> This is the rater instrument, so " +
    "you can review the questions, the wording and the flow. What to ignore: each " +
    "video unlocks after about <strong>5%</strong> has played rather than 90%, so " +
    "this takes a couple of minutes instead of 25; the two videos are from " +
    "different courses rather than two versions of one, so “which was better” " +
    "is meaningless here; the code-word question is optional, because you will " +
    "not watch far enough in to see one; and this preview does not save your place, " +
    "so walk it in one go - the real study does resume if a rater loses power, but " +
    "saving here would drop the next person who opens this shared link into your " +
    "half-finished session. Everything else is exactly what a paid " +
    "rater gets: the same videos, the watch gate, the skip-blocking, the black " +
    "“Part 2” pause halfway through each video, and every question. Your " +
    "answers are tagged as a preview and excluded from the analysis automatically.",

  /* The REAL joined videos now, so a reviewer sees exactly what a rater sees: one
     player per section, each running module 1, a black "Part 2" pause, then module 3.
     Still stand-ins in one respect - these are two DIFFERENT courses rather than two
     versions of one - so "which was better" remains meaningless here. Both happen to
     be the current build, which also means nothing about old-vs-new is on display.

     What IS real: the videos themselves, the watch gate, the skip-rewind, captions
     forced off, the code word box under the player, the four labelled rating scales,
     the conditional narration follow-up, and the whole end block. */
  pairs: [
    {
      id: "P2", cc: "DEMO", enabled: true,
      versions: [
        { key: "k2wj", yts: ["Umcwa2hOGyY"] },
        { key: "k8rn", yts: ["EmbyxGru4u4"] }
      ]
    }
  ]
};
