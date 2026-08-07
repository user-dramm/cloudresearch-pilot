/* ============================================================================
   STUDY CONFIG: Embrace Pilot 2026-07, blind old-vs-new, 5 CC course pairs
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
     Only genuine playback counts, and seeking forward earns no credit. */
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

     Each version is ONE video: module 1, a 2.5s black pause labelled "Part 2",
     then module 3. Joined rather than served as two files so a section needs only
     one player and there are 10 uploads instead of 20. The list form is kept in
     case a section ever needs more than one file again:

       yts:  [ "oneJoinedVideoId" ]                    [youtube mode]
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
      id: "P1", cc: "EMBR-CC-00051", enabled: true,
      versions: [
        { key: "k3ta", yts: ["Umcwa2hOGyY"], srcs: ["", ""] },
        { key: "k9vm", yts: ["v2f_xx6Qt3U"], srcs: ["", ""] }
      ]
    },
    {
      id: "P2", cc: "EMBR-CC-00158", enabled: true,
      versions: [
        { key: "k5qd", yts: ["yUKJ5gmt-XU"],
                       srcs: ["", ""] },
        { key: "k2wj", yts: ["6DqvPsedtk4"],
                       srcs: ["", ""] }
      ]
    },
    {
      id: "P3", cc: "EMBR-CC-00162", enabled: true,
      versions: [
        { key: "k8rn", yts: ["EmbyxGru4u4"],
                       srcs: ["", ""] },
        { key: "k4zf", yts: ["WjEVeO5bq0U"],
                       srcs: ["", ""] }
      ]
    },
    /* Was EMBR-CC-00175 (Cognitive Challenges in Huntington's Disease), swapped
       2026-08-05 for EMBR-CC-00176 (Movement Challenges in Parkinson's Disease).
       Both codes exist in Airtable and both are 3-module, 15-minute courses; 176
       is the one being taken forward. */
    {
      id: "P4", cc: "EMBR-CC-00176", enabled: true,
      versions: [
        { key: "k6hb", yts: ["za7CpasFUM4"], srcs: ["", ""] },
        { key: "k1ps", yts: ["a8-Pi02DFsQ"], srcs: ["", ""] }
      ]
    },
    {
      id: "P5", cc: "EMBR-CC-00254", enabled: true,
      versions: [
        { key: "k7cy", yts: ["pe3snqlh_zY"],
                       srcs: ["", ""] },
        { key: "k0lg", yts: ["yE06txRZaNQ"],
                       srcs: ["", ""] }
      ]
    }
  ]
};
