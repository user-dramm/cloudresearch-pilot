/* ============================================================================
   DEMO CONFIG — a preview build for colleagues to walk. NOT the study.
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

     videos       THROWAWAY uploads. Delete them before the real study's upload
                  session. The real twelve must all be uploaded together in one
                  sitting, because upload dates are the classic way a blind study
                  leaks: if some clips are from today and some from last month, a
                  curious rater can work out which version is older. Reusing these
                  demo uploads in the study would break that.

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
    "this takes a couple of minutes instead of 25; the two videos are unrelated " +
    "stand-ins rather than two versions of one course, so “which was better” " +
    "is meaningless here; the code-word question is optional because you will not " +
    "watch far enough in to see one; and the real videos run in two parts with a " +
    "short black pause, which these stand-ins do not. Everything else — the watch " +
    "gate, the skip-blocking, the questions and the follow-ups — is exactly what a " +
    "paid rater gets. Your answers are tagged as a preview and excluded from the " +
    "analysis automatically.",

  /* ONE video per section, matching the real structure: each side is a single
     player, not two. These are stand-ins - two unrelated courses, and single modules
     rather than the joined two-part files - because the joined videos are not
     uploaded yet. So "which was better" is meaningless here.

     What IS real: the watch gate, the skip-rewind, captions forced off, the four
     labelled rating scales, the optional open question, the speaker question and its
     conditional probe, and the whole end block. Those are what a reviewer should be
     looking at. */
  pairs: [
    {
      id: "P2", cc: "DEMO", enabled: true,
      versions: [
        { key: "k2wj", yts: ["dlRP9lEVEgY"] },
        { key: "k8rn", yts: ["zDVyC079umo"] }
      ]
    }
  ]
};
