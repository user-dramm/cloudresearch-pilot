/* ============================================================================
   STUDY CONFIG — Embrace Pilot 2026-07, blind old-vs-new, 5 CC course pairs
   ----------------------------------------------------------------------------
   This file is PUBLIC (it ships to the participant's browser). Nothing in here
   may reveal which version is old and which is new. Version keys are opaque on
   purpose; the old/new mapping lives in decode_key.json, which is gitignored
   and used only by analysis.py.
   ============================================================================ */

window.STUDY_CONFIG = {

  studyTag: "pilot-2026-07",

  /* "file" = self-hosted MP4s via a plain <video> tag (recommended: tighter
     blinding, real seek-blocking, no third-party dependency).
     "youtube" = unlisted YouTube embeds via the IFrame API (zero infrastructure,
     adaptive bitrate on bad connections). Switching is one word; the gate,
     the data schema, and the analysis are identical either way.
     Currently YOUTUBE: see the upload discipline checklist in README, which is
     what closes the blinding gap this backend leaves open. */
  videoSource: "youtube",

  /* file mode only: rewind any attempt to scrub past the furthest point
     genuinely watched. YouTube mode can't do this - it can only decline to
     credit the skipped time. */
  blockSeeking: true,

  /* Paste the Apps Script web-app /exec URL here after deploying.
     This URL is public by design. The endpoint is append-only; see Code.gs. */
  endpoint: "https://script.google.com/macros/s/AKfycbzlJjh67g33lmEEJslD9JhMhKQj3lulof4UAXlZ12auC4_7D7DX4DEQskGpdES2n3Zx/exec",

  /* Weak bot filter, not security. Must match TOKEN in Code.gs. */
  formToken: "embr-pilot-2026-07",

  /* Shown once a response is confirmed saved. Must match the fixed code you set
     in Connect. Connect disallows 0, 1, I and O in fixed codes - this one is clean. */
  completionCode: "EMBR7K2QX4",

  /* Paste the Redirect URL from the end of Connect's Create-a-Study wizard.
     Connect calls this the most reliable completion method: the participant is
     sent back automatically instead of having to copy the code across. Leave it
     empty to fall back to code-only. */
  redirectUrl: "",

  /* Fraction of each clip that must actually play before questions unlock.
     Only genuine playback counts — seeking forward earns no credit. */
  watchGate: 0.90,

  /* Minimum characters for the free-text answers (quality gate). */
  minCommentChars: 60,
  minWhyChars: 80,

  /* ------------------------------------------------------------------------
     PAIRS
     - enabled:false pairs are auto-excluded from random assignment, so an
       unfinished pair can sit here harmlessly until its clips exist.
     - versions: exactly two entries, one per build of the course. The keys are
       opaque labels you invent; do not name them old/new. Record the true
       mapping in decode_key.json.

     Each version is shown to the rater as a SECTION of two videos - module 1
     then module 3 - watched back to back before any question is asked, because
     what the study compares is the VERSION, not a single module. So each version
     carries a LIST, in the order they should be watched:

       yts:  [ "moduleOneId", "moduleThreeId" ]        [youtube mode]
       srcs: [ "https://.../m1.mp4", ".../m3.mp4" ]    [file mode]

     Only the list matching videoSource has to be filled in. A single `yt` or
     `src` string is still accepted and means a one-video section.

     A version goes live only when EVERY video in it is real, so a half-filled
     one can sit here harmlessly - a missing module 3 would otherwise let a rater
     judge a version on half the material and the row would look complete.

     ORDER MATTERS: the code word is burned into the SECOND video of each section.
     ------------------------------------------------------------------------ */
  pairs: [
    {
      id: "P1", cc: "EMBR-CC-00051", enabled: false,
      versions: [
        { key: "k3ta", yts: ["", ""], srcs: ["", ""] },
        { key: "k9vm", yts: ["", ""], srcs: ["", ""] }
      ]
    },
    {
      id: "P2", cc: "EMBR-CC-00158", enabled: true,
      versions: [
        { key: "k5qd", yts: ["REPLACE_YT_ID", "REPLACE_YT_ID"],
                       srcs: ["https://clips.example.com/k5qd_m1.mp4",
                              "https://clips.example.com/k5qd_m3.mp4"] },
        { key: "k2wj", yts: ["REPLACE_YT_ID", "REPLACE_YT_ID"],
                       srcs: ["https://clips.example.com/k2wj_m1.mp4",
                              "https://clips.example.com/k2wj_m3.mp4"] }
      ]
    },
    {
      id: "P3", cc: "EMBR-CC-00162", enabled: true,
      versions: [
        { key: "k8rn", yts: ["REPLACE_YT_ID", "REPLACE_YT_ID"],
                       srcs: ["https://clips.example.com/k8rn_m1.mp4",
                              "https://clips.example.com/k8rn_m3.mp4"] },
        { key: "k4zf", yts: ["REPLACE_YT_ID", "REPLACE_YT_ID"],
                       srcs: ["https://clips.example.com/k4zf_m1.mp4",
                              "https://clips.example.com/k4zf_m3.mp4"] }
      ]
    },
    /* Was EMBR-CC-00175 (Cognitive Challenges in Huntington's Disease), swapped
       2026-08-05 for EMBR-CC-00176 (Movement Challenges in Parkinson's Disease).
       Both codes exist in Airtable and both are 3-module, 15-minute courses; 176
       is the one being taken forward. Still disabled: only its archived side has
       been supplied, so there is nothing to compare against yet. */
    {
      id: "P4", cc: "EMBR-CC-00176", enabled: false,
      versions: [
        { key: "k6hb", yts: ["", ""], srcs: ["", ""] },
        { key: "k1ps", yts: ["", ""], srcs: ["", ""] }
      ]
    },
    {
      id: "P5", cc: "EMBR-CC-00254", enabled: true,
      versions: [
        { key: "k7cy", yts: ["REPLACE_YT_ID", "REPLACE_YT_ID"],
                       srcs: ["https://clips.example.com/k7cy_m1.mp4",
                              "https://clips.example.com/k7cy_m3.mp4"] },
        { key: "k0lg", yts: ["REPLACE_YT_ID", "REPLACE_YT_ID"],
                       srcs: ["https://clips.example.com/k0lg_m1.mp4",
                              "https://clips.example.com/k0lg_m3.mp4"] }
      ]
    }
  ]
};
