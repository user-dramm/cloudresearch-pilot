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
    "<strong>Preview, not the real study.</strong> You are looking at the rater " +
    "instrument so you can review the questions, the wording and the flow. Three " +
    "differences from the live version: each video unlocks after about " +
    "<strong>5%</strong> of it has played rather than 90%, so the whole thing takes " +
    "a couple of minutes; the two videos in a set are unrelated stand-ins, so the " +
    "“which set was better” answer is meaningless here; and the code-word " +
    "question is optional, because the code word appears halfway through a video you " +
    "will not have watched that far into. Everything else — the watch gate, the " +
    "skip-blocking, the questions, the conditional follow-ups — is exactly what a " +
    "paid rater will get. Your answers are tagged as a preview and are excluded " +
    "from the analysis automatically.",

  /* Real uploads, but NOT a real pair. Both sets below are the CURRENT build of
     two DIFFERENT courses (00158 and 00162), because at the time this was wired up
     no course had both of its sides uploaded. So the "which set was better"
     question compares unrelated material and its answer is meaningless.

     Everything else is the genuine article: real videos, real durations, real code
     words burned in at 45% of each second video, the real watch gate, the real
     question set and the real conditional follow-ups.

     Code words a reviewer will actually see:
       set 1 (k2wj, 00158 module 3) -> juniper
       set 2 (k8rn, 00162 module 3) -> kettle

     Order inside a set matters: module 1 first, then module 3, which is the one
     carrying the code word. */
  pairs: [
    {
      id: "P2", cc: "DEMO", enabled: true,
      versions: [
        { key: "k2wj", yts: ["elN8cuwcDSE", "dlRP9lEVEgY"] },
        { key: "k8rn", yts: ["qHwWmi8mugA", "zDVyC079umo"] }
      ]
    }
  ]
};
