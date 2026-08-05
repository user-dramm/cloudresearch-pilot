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

     watchGate    0.15 instead of 0.90, so a reviewer meets the gate in about 40
                  seconds per video rather than four minutes. The banner says so
                  on screen; without that a reviewer would reasonably report the
                  gate as broken.

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

  /* 15% instead of 90%. NOT the study value - see the banner. */
  watchGate: 0.15,

  minCommentChars: 60,
  minWhyChars: 80,

  demoBanner:
    "<strong>Preview, not the real study.</strong> You are looking at the rater " +
    "instrument so you can review the questions, the wording and the flow. Two " +
    "differences from the live version: each video unlocks after about " +
    "<strong>15%</strong> of it has played rather than 90%, so you are not here for " +
    "20 minutes; and the two videos in a set are unrelated stand-ins, so the " +
    "“which set was better” answer is meaningless here. Everything else " +
    "— the watch gate, the questions, the conditional follow-ups — is exactly " +
    "what a paid rater will get. Your answers are tagged as a preview and are " +
    "excluded from the analysis automatically.",

  /* Fill in the four throwaway YouTube IDs. Order matters inside each set:
     the code word is burned into the SECOND video of a set. */
  pairs: [
    {
      id: "P2", cc: "DEMO", enabled: true,
      versions: [
        { key: "k5qd", yts: ["REPLACE_YT_ID", "REPLACE_YT_ID"] },
        { key: "k2wj", yts: ["REPLACE_YT_ID", "REPLACE_YT_ID"] }
      ]
    }
  ]
};
